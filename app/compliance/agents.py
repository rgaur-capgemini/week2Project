"""
Agentic Compliance Report Generation using LangGraph.
Multi-node workflow for autonomous document compliance checking.
"""

from typing import TypedDict, List, Dict, Annotated, Literal, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator

from app.rag.embeddings import VertexTextEmbedder
from app.rag.vector_store import VertexVectorStore
from app.rag.generator import GeminiGenerator
from app.compliance.template_matcher import TemplateMatcher
from app.compliance.gap_analyzer import GapAnalyzer
from app.compliance.report_generator import ComplianceReportGenerator
from app.logging_config import get_logger

logger = get_logger(__name__)


class ComplianceState(TypedDict):
    """State for compliance workflow."""
    document_id: str
    document_text: str
    template_type: Optional[str]
    
    # Retrieval state
    relevant_templates: List[Dict]
    
    # Analysis state
    matched_sections: List[Dict]
    gaps: List[Dict]
    compliance_score: float
    
    # Generation state
    report: str
    recommendations: List[str]
    
    # Metadata
    messages: Annotated[List[BaseMessage], operator.add]
    iteration: int
    max_iterations: int
    status: str


class ComplianceAgent:
    """
    Multi-agent system for compliance report generation.
    
    Workflow:
    1. Template Retrieval Agent - Find relevant compliance templates
    2. Matching Agent - Match document sections to template requirements
    3. Gap Analysis Agent - Identify missing/non-compliant sections
    4. Report Generation Agent - Create comprehensive compliance report
    5. Review Agent - Self-check and refine report
    """
    
    def __init__(
        self,
        embeddings: VertexTextEmbedder,
        template_vector_store: VertexVectorStore,
        document_vector_store: VertexVectorStore,
        generator: GeminiGenerator,
        max_iterations: int = 2
    ):
        """
        Initialize compliance agent.
        
        Args:
            embeddings: Text embedder
            template_vector_store: Vector store for templates
            document_vector_store: Vector store for documents
            generator: Gemini generator
            max_iterations: Maximum refinement iterations
        """
        self.embeddings = embeddings
        self.template_vector_store = template_vector_store
        self.document_vector_store = document_vector_store
        self.generator = generator
        self.max_iterations = max_iterations
        
        # Initialize sub-components
        self.template_matcher = TemplateMatcher(embeddings, similarity_threshold=0.75)
        self.gap_analyzer = GapAnalyzer(high_threshold=0.85, medium_threshold=0.75)
        self.report_generator = ComplianceReportGenerator(generator)
        
        # Build workflow graph
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()
        
        logger.info("ComplianceAgent initialized with LangGraph workflow")
    
    def _build_graph(self) -> StateGraph:
        """Build the compliance workflow graph."""
        workflow = StateGraph(ComplianceState)
        
        # Add nodes
        workflow.add_node("retrieve_templates", self._retrieve_templates_node)
        workflow.add_node("match_sections", self._match_sections_node)
        workflow.add_node("analyze_gaps", self._analyze_gaps_node)
        workflow.add_node("generate_report", self._generate_report_node)
        workflow.add_node("review_report", self._review_report_node)
        
        # Add edges
        workflow.set_entry_point("retrieve_templates")
        workflow.add_edge("retrieve_templates", "match_sections")
        workflow.add_edge("match_sections", "analyze_gaps")
        workflow.add_edge("analyze_gaps", "generate_report")
        workflow.add_edge("generate_report", "review_report")
        
        # Conditional edge: retry if review suggests improvements
        workflow.add_conditional_edges(
            "review_report",
            self._should_refine,
            {
                "refine": "generate_report",  # Loop back for refinement
                "complete": END
            }
        )
        
        logger.info("LangGraph workflow built with 5 nodes")
        return workflow
    
    def _retrieve_templates_node(self, state: ComplianceState) -> ComplianceState:
        """Agent 1: Retrieve relevant compliance templates."""
        
        try:
            logger.info(f"Retrieving templates for document {state['document_id']}")
            
            # Use document intro for template search
            search_text = state["document_text"][:2000]  # First 2000 chars
            
            # Search template vector store
            template_results = self.template_vector_store.search(
                query=search_text,
                top_k=10,
                enable_pii_filter=False  # Templates are pre-approved
            )
            
            # Filter by template type if specified
            if state.get("template_type"):
                template_results = [
                    t for t in template_results 
                    if t.get("metadata", {}).get("template_type") == state["template_type"]
                ]
                logger.info(f"Filtered to template_type={state['template_type']}: {len(template_results)} templates")
            
            state["relevant_templates"] = template_results
            state["messages"].append(
                AIMessage(content=f"Retrieved {len(template_results)} relevant compliance templates")
            )
            state["status"] = "templates_retrieved"
            
            logger.info(f"Retrieved {len(template_results)} templates")
            
        except Exception as e:
            logger.error(f"Error retrieving templates: {e}", exc_info=True)
            state["relevant_templates"] = []
            state["messages"].append(AIMessage(content=f"Error retrieving templates: {str(e)}"))
            state["status"] = "error"
        
        return state
    
    def _match_sections_node(self, state: ComplianceState) -> ComplianceState:
        """Agent 2: Match document sections to template requirements."""
        
        try:
            logger.info(f"Matching document sections to {len(state['relevant_templates'])} templates")
            
            if not state["relevant_templates"]:
                logger.warning("No templates available for matching")
                state["matched_sections"] = []
                state["messages"].append(AIMessage(content="No templates available for matching"))
                return state
            
            matched_sections = self.template_matcher.match(
                document_text=state["document_text"],
                templates=state["relevant_templates"],
                top_k=5
            )
            
            state["matched_sections"] = matched_sections
            state["messages"].append(
                AIMessage(content=f"Matched {len(matched_sections)} requirements to document sections")
            )
            state["status"] = "sections_matched"
            
            logger.info(f"Matched {len(matched_sections)} sections")
            
        except Exception as e:
            logger.error(f"Error matching sections: {e}", exc_info=True)
            state["matched_sections"] = []
            state["messages"].append(AIMessage(content=f"Error matching sections: {str(e)}"))
            state["status"] = "error"
        
        return state
    
    def _analyze_gaps_node(self, state: ComplianceState) -> ComplianceState:
        """Agent 3: Identify compliance gaps."""
        
        try:
            logger.info(f"Analyzing gaps for {len(state['matched_sections'])} matched sections")
            
            if not state["matched_sections"]:
                logger.warning("No matched sections available for gap analysis")
                state["gaps"] = []
                state["compliance_score"] = 0.0
                state["messages"].append(AIMessage(content="No matched sections for gap analysis"))
                return state
            
            gaps, compliance_score = self.gap_analyzer.analyze(
                matched_sections=state["matched_sections"],
                templates=state["relevant_templates"]
            )
            
            state["gaps"] = gaps
            state["compliance_score"] = compliance_score
            state["messages"].append(
                AIMessage(content=f"Compliance score: {compliance_score:.1f}%, identified {len(gaps)} gaps")
            )
            state["status"] = "gaps_analyzed"
            
            logger.info(f"Analyzed gaps: score={compliance_score:.1f}%, gaps={len(gaps)}")
            
        except Exception as e:
            logger.error(f"Error analyzing gaps: {e}", exc_info=True)
            state["gaps"] = []
            state["compliance_score"] = 0.0
            state["messages"].append(AIMessage(content=f"Error analyzing gaps: {str(e)}"))
            state["status"] = "error"
        
        return state
    
    def _generate_report_node(self, state: ComplianceState) -> ComplianceState:
        """Agent 4: Generate compliance report."""
        
        try:
            logger.info(f"Generating compliance report for document {state['document_id']}")
            
            report, recommendations = self.report_generator.generate(
                document_id=state["document_id"],
                matched_sections=state["matched_sections"],
                gaps=state["gaps"],
                compliance_score=state["compliance_score"],
                templates=state["relevant_templates"]
            )
            
            state["report"] = report
            state["recommendations"] = recommendations
            state["messages"].append(
                AIMessage(content=f"Generated compliance report ({len(report)} chars, {len(recommendations)} recommendations)")
            )
            state["status"] = "report_generated"
            
            logger.info(f"Generated report: {len(report)} chars, {len(recommendations)} recommendations")
            
        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            state["report"] = f"# Error Generating Report\n\nAn error occurred: {str(e)}"
            state["recommendations"] = []
            state["messages"].append(AIMessage(content=f"Error generating report: {str(e)}"))
            state["status"] = "error"
        
        return state
    
    def _review_report_node(self, state: ComplianceState) -> ComplianceState:
        """Agent 5: Review and potentially refine report."""
        
        try:
            logger.info(f"Reviewing report quality (iteration {state.get('iteration', 0)})")
            
            # Simple review - check report length and key sections
            report = state["report"]
            
            # Check for key sections
            required_sections = ["Executive Summary", "Compliance Score", "Gaps", "Recommendations"]
            has_required = all(section.lower() in report.lower() for section in required_sections)
            
            if has_required and len(report) > 500:
                review_result = "APPROVED - Report contains all required sections"
                state["status"] = "completed"
            else:
                review_result = "REFINE - Report missing sections or too brief"
                state["status"] = "refining"
            
            state["messages"].append(AIMessage(content=f"Review: {review_result}"))
            state["iteration"] = state.get("iteration", 0) + 1
            
            logger.info(f"Review complete: {review_result}")
            
        except Exception as e:
            logger.error(f"Error reviewing report: {e}", exc_info=True)
            state["messages"].append(AIMessage(content=f"Review error: {str(e)}"))
            state["status"] = "completed"  # Complete despite error
            state["iteration"] = state.get("iteration", 0) + 1
        
        return state
    
    def _should_refine(self, state: ComplianceState) -> Literal["refine", "complete"]:
        """Decide whether to refine report or complete."""
        
        # Check iteration limit
        if state.get("iteration", 0) >= self.max_iterations:
            logger.info(f"Max iterations reached ({self.max_iterations}), completing")
            return "complete"
        
        # Check if review suggests refinement
        if state.get("messages"):
            last_message = state["messages"][-1]
            # Safely extract content from BaseMessage or dict
            content = last_message.content if hasattr(last_message, 'content') else str(last_message)
            if "REFINE" in str(content).upper():
                logger.info("Review suggests refinement, looping back")
                return "refine"
        
        logger.info("Review approved, completing")
        return "complete"
    
    async def run(
        self,
        document_id: str,
        document_text: str,
        template_type: Optional[str] = None
    ) -> Dict:
        """
        Execute compliance workflow.
        
        Args:
            document_id: Document identifier
            document_text: Full document text
            template_type: Optional template type filter
        
        Returns:
            Dictionary with compliance analysis results
        """
        try:
            logger.info(f"Starting compliance workflow for document {document_id}")
            
            initial_state = ComplianceState(
                document_id=document_id,
                document_text=document_text,
                template_type=template_type,
                relevant_templates=[],
                matched_sections=[],
                gaps=[],
                compliance_score=0.0,
                report="",
                recommendations=[],
                messages=[HumanMessage(content=f"Analyze compliance for document {document_id}")],
                iteration=0,
                max_iterations=self.max_iterations,
                status="started"
            )
            
            # Execute workflow
            final_state = await self.app.ainvoke(initial_state)
            
            result = {
                "document_id": final_state["document_id"],
                "compliance_score": final_state["compliance_score"],
                "report": final_state["report"],
                "recommendations": final_state["recommendations"],
                "gaps": final_state["gaps"],
                "matched_sections": final_state["matched_sections"],
                "status": final_state.get("status", "completed"),
                "templates_used": len(final_state["relevant_templates"])
            }
            
            logger.info(f"Compliance workflow completed: score={result['compliance_score']:.1f}%, status={result['status']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in compliance workflow: {e}", exc_info=True)
            return {
                "document_id": document_id,
                "compliance_score": 0.0,
                "report": f"# Error\n\nCompliance analysis failed: {str(e)}",
                "recommendations": [],
                "gaps": [],
                "matched_sections": [],
                "status": "error",
                "templates_used": 0,
                "error": str(e)
            }
    
    def run_sync(
        self,
        document_id: str,
        document_text: str,
        template_type: Optional[str] = None
    ) -> Dict:
        """
        Synchronous version of run method.
        
        Args:
            document_id: Document identifier
            document_text: Full document text
            template_type: Optional template type filter
        
        Returns:
            Dictionary with compliance analysis results
        """
        try:
            logger.info(f"Starting synchronous compliance workflow for document {document_id}")
            
            initial_state = ComplianceState(
                document_id=document_id,
                document_text=document_text,
                template_type=template_type,
                relevant_templates=[],
                matched_sections=[],
                gaps=[],
                compliance_score=0.0,
                report="",
                recommendations=[],
                messages=[HumanMessage(content=f"Analyze compliance for document {document_id}")],
                iteration=0,
                max_iterations=self.max_iterations,
                status="started"
            )
            
            # Execute workflow synchronously
            final_state = self.app.invoke(initial_state)
            
            result = {
                "document_id": final_state["document_id"],
                "compliance_score": final_state["compliance_score"],
                "report": final_state["report"],
                "recommendations": final_state["recommendations"],
                "gaps": final_state["gaps"],
                "matched_sections": final_state["matched_sections"],
                "status": final_state.get("status", "completed"),
                "templates_used": len(final_state["relevant_templates"])
            }
            
            logger.info(f"Compliance workflow completed: score={result['compliance_score']:.1f}%, status={result['status']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in compliance workflow: {e}", exc_info=True)
            return {
                "document_id": document_id,
                "compliance_score": 0.0,
                "report": f"# Error\n\nCompliance analysis failed: {str(e)}",
                "recommendations": [],
                "gaps": [],
                "matched_sections": [],
                "status": "error",
                "templates_used": 0,
                "error": str(e)
            }
