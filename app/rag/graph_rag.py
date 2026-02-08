"""
LangGraph-based RAG Pipeline with Vertex AI Integration
Provides stateful, cyclic workflow for advanced RAG patterns
"""

from typing import TypedDict, List, Dict, Any, Annotated, Tuple
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator

from app.rag.embeddings import VertexTextEmbedder
from app.rag.vector_store import VertexVectorStore
from app.rag.reranker import HybridReranker
from app.rag.generator import GeminiGenerator


class RAGState(TypedDict):
    """State for RAG workflow"""
    messages: Annotated[List[BaseMessage], operator.add]
    query: str
    retrieved_docs: List[Dict[str, Any]]
    reranked_docs: List[Dict[str, Any]]
    context: str
    response: str
    confidence_score: float
    needs_refinement: bool
    iteration: int


class LangGraphRAGPipeline:
    """
    LangGraph-based RAG pipeline with:
    - Stateful conversation memory
    - Adaptive retrieval (can loop if confidence low)
    - Self-correction capabilities
    - Integration with existing GCP Vertex AI components
    """
    
    def __init__(
        self,
        embeddings: VertexTextEmbedder,
        vector_store: VertexVectorStore,
        reranker: HybridReranker,
        generator: GeminiGenerator,
        max_iterations: int = 2
    ):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.reranker = reranker
        self.generator = generator
        self.max_iterations = max_iterations
        
        # Build the graph
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile()
    
    def _build_graph(self) -> StateGraph:
        """Build the RAG workflow graph"""
        workflow = StateGraph(RAGState)
        
        # Add nodes
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("rerank", self._rerank_node)
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("evaluate", self._evaluate_node)
        workflow.add_node("refine_query", self._refine_query_node)
        
        # Define edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", "generate")
        workflow.add_edge("generate", "evaluate")
        
        # Conditional edge: refine or finish
        workflow.add_conditional_edges(
            "evaluate",
            self._should_refine,
            {
                "refine": "refine_query",
                "finish": END
            }
        )
        workflow.add_edge("refine_query", "retrieve")
        
        return workflow
    
    def _retrieve_node(self, state: RAGState) -> RAGState:
        """Retrieve relevant documents from Vector Search"""
        query = state["query"]
        
        # Use existing vector store search
        results = self.vector_store.search(query, top_k=10)
        
        state["retrieved_docs"] = results
        return state
    
    def _rerank_node(self, state: RAGState) -> RAGState:
        """Rerank retrieved documents"""
        query = state["query"]
        docs = state["retrieved_docs"]
        
        # Use existing reranker - returns List[Dict] with reranked chunks
        reranked = self.reranker.rerank(
            query=query,
            chunks=docs,
            top_k=5
        )
        
        state["reranked_docs"] = reranked
        state["context"] = "\n\n".join([d["text"] for d in reranked])
        return state
    
    def _generate_node(self, state: RAGState) -> RAGState:
        """Generate response using Vertex AI Gemini"""
        query = state["query"]
        context = state["context"]
        
        # GeminiGenerator.generate returns (response, citations, token_usage)
        response, citations, token_usage = self.generator.generate(
            question=query,
            contexts=context if isinstance(context, list) else [context]
        )
        
        state["response"] = response
        state["messages"].append(HumanMessage(content=query))
        state["messages"].append(AIMessage(content=response))
        
        return state
    
    def _evaluate_node(self, state: RAGState) -> RAGState:
        """Evaluate response quality and decide if refinement needed"""
        # Simple heuristic: check if response is too short or generic
        response = state["response"]
        context = state["context"]
        
        # Calculate confidence based on:
        # 1. Response length (should have substance)
        # 2. Context relevance (retrieved docs should be used)
        # 3. Number of iterations (don't loop forever)
        
        confidence = 1.0
        
        if len(response) < 50:
            confidence -= 0.3
        
        if not context or len(context) < 100:
            confidence -= 0.4
        
        if "I don't have enough information" in response.lower():
            confidence -= 0.5
        
        state["confidence_score"] = confidence
        state["needs_refinement"] = (
            confidence < 0.6 and 
            state.get("iteration", 0) < self.max_iterations
        )
        state["iteration"] = state.get("iteration", 0) + 1
        
        return state
    
    def _refine_query_node(self, state: RAGState) -> RAGState:
        """Refine the query for better retrieval"""
        original_query = state["query"]
        
        # Use LLM to expand/refine the query
        refinement_prompt = f"""Given the original query: "{original_query}"

The initial search didn't find sufficient information. 
Generate 2-3 alternative phrasings or expanded versions that might retrieve better results.
Return only the best refined query (one sentence)."""
        
        refined, _, _ = self.generator.generate(
            question=refinement_prompt,
            contexts=[]
        )
        refined = refined.strip()
        
        state["query"] = refined
        return state
    
    def _should_refine(self, state: RAGState) -> str:
        """Decide whether to refine query or finish"""
        return "refine" if state["needs_refinement"] else "finish"
    
    async def query(self, query: str, chat_history: List[Tuple[str, str]] = None) -> Dict[str, Any]:
        """
        Execute the RAG pipeline with stateful workflow
        
        Args:
            query: User query
            chat_history: Previous conversation turns
            
        Returns:
            Dict with response, sources, confidence, and metadata
        """
        # Initialize state
        initial_state = RAGState(
            messages=[
                HumanMessage(content=q) if i % 2 == 0 else AIMessage(content=a)
                for i, (q, a) in enumerate(chat_history or [])
            ],
            query=query,
            retrieved_docs=[],
            reranked_docs=[],
            context="",
            response="",
            confidence_score=0.0,
            needs_refinement=False,
            iteration=0
        )
        
        # Run the graph
        final_state = self.compiled_graph.invoke(initial_state)
        
        # Format response
        return {
            "response": final_state["response"],
            "sources": [
                {
                    "text": doc["text"][:200] + "...",
                    "metadata": doc.get("metadata", {}),
                    "score": doc.get("rerank_score", 0.0)
                }
                for doc in final_state["reranked_docs"][:3]
            ],
            "confidence": final_state["confidence_score"],
            "iterations": final_state["iteration"],
            "final_query": final_state["query"]
        }

