"""
Compliance report generation using Gemini.
Creates professional compliance reports in Markdown format.
"""

from typing import List, Dict, Tuple
from datetime import datetime
from app.rag.generator import GeminiGenerator
from app.logging_config import get_logger

logger = get_logger(__name__)


class ComplianceReportGenerator:
    """Generate structured compliance reports using LLM."""
    
    def __init__(self, generator: GeminiGenerator):
        """
        Initialize report generator.
        
        Args:
            generator: Gemini generator for report creation
        """
        self.generator = generator
        logger.info("ComplianceReportGenerator initialized")
    
    def generate(
        self,
        document_id: str,
        matched_sections: List[Dict],
        gaps: List[Dict],
        compliance_score: float,
        templates: List[Dict]
    ) -> Tuple[str, List[str]]:
        """
        Generate comprehensive compliance report.
        
        Args:
            document_id: Document identifier
            matched_sections: Matched sections from template matcher
            gaps: Identified gaps from gap analyzer
            compliance_score: Overall compliance score (0-100)
            templates: Original templates used
        
        Returns:
            Tuple of (report_markdown, recommendations_list)
        """
        try:
            logger.info(f"Generating compliance report for document {document_id}")
            
            # Build context for LLM
            context = self._build_context(document_id, matched_sections, gaps, compliance_score, templates)
            
            # Generate report using Gemini
            report_prompt = self._create_report_prompt(compliance_score, len(matched_sections), len(gaps))
            
            report, _, _ = self.generator.generate(
                question=report_prompt,
                contexts=[context],
                temperature=0.3  # Low temperature for factual, consistent reports
            )
            
            # Extract recommendations
            recommendations = self._extract_recommendations(gaps)
            
            # Add metadata section
            report_with_metadata = self._add_metadata_section(report, document_id, compliance_score)
            
            logger.info(f"Report generated: {len(report_with_metadata)} chars, {len(recommendations)} recommendations")
            
            return report_with_metadata, recommendations
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}", exc_info=True)
            # Return fallback report
            fallback_report = self._generate_fallback_report(document_id, compliance_score, gaps)
            return fallback_report, self._extract_recommendations(gaps)
    
    def _build_context(
        self,
        document_id: str,
        matched_sections: List[Dict],
        gaps: List[Dict],
        compliance_score: float,
        templates: List[Dict]
    ) -> str:
        """Build context string for LLM."""
        
        # Summary statistics
        total_requirements = len(matched_sections)
        compliant = sum(1 for s in matched_sections if s.get("status") == "compliant")
        partial = sum(1 for s in matched_sections if s.get("status") == "partial")
        missing = total_requirements - compliant - partial
        
        # Categorize gaps by severity
        high_gaps = [g for g in gaps if g.get("severity") == "high"]
        medium_gaps = [g for g in gaps if g.get("severity") == "medium"]
        low_gaps = [g for g in gaps if g.get("severity") == "low"]
        
        context_parts = [
            f"COMPLIANCE ANALYSIS REPORT",
            f"Document ID: {document_id}",
            f"Analysis Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"",
            f"OVERALL COMPLIANCE SCORE: {compliance_score:.1f}%",
            f"",
            f"SUMMARY STATISTICS:",
            f"- Total Requirements: {total_requirements}",
            f"- Fully Compliant: {compliant} ({compliant/total_requirements*100:.1f}%)" if total_requirements > 0 else "- Fully Compliant: 0",
            f"- Partially Compliant: {partial} ({partial/total_requirements*100:.1f}%)" if total_requirements > 0 else "- Partially Compliant: 0",
            f"- Non-Compliant/Missing: {missing} ({missing/total_requirements*100:.1f}%)" if total_requirements > 0 else "- Non-Compliant/Missing: 0",
            f"",
            f"GAP ANALYSIS:",
            f"- High Severity Gaps: {len(high_gaps)}",
            f"- Medium Severity Gaps: {len(medium_gaps)}",
            f"- Low Severity Gaps: {len(low_gaps)}",
            f"",
            f"COMPLIANT SECTIONS (Top 10):",
        ]
        
        # Add top compliant sections
        compliant_sections = [s for s in matched_sections if s.get("status") == "compliant"]
        compliant_sections.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        
        for i, section in enumerate(compliant_sections[:10], 1):
            context_parts.append(
                f"{i}. {section.get('requirement_id')}: {section.get('requirement_text', '')[:100]}... "
                f"(Score: {section.get('similarity_score', 0):.2f})"
            )
        
        context_parts.append("")
        context_parts.append("IDENTIFIED GAPS (By Severity):")
        context_parts.append("")
        
        # Add high severity gaps
        if high_gaps:
            context_parts.append("HIGH SEVERITY:")
            for gap in high_gaps[:5]:
                context_parts.append(
                    f"- [{gap.get('requirement_id')}] {gap.get('requirement', '')[:150]}"
                )
        
        # Add medium severity gaps
        if medium_gaps:
            context_parts.append("")
            context_parts.append("MEDIUM SEVERITY:")
            for gap in medium_gaps[:5]:
                context_parts.append(
                    f"- [{gap.get('requirement_id')}] {gap.get('requirement', '')[:150]}"
                )
        
        # Add low severity gaps
        if low_gaps:
            context_parts.append("")
            context_parts.append("LOW SEVERITY:")
            for gap in low_gaps[:5]:
                context_parts.append(
                    f"- [{gap.get('requirement_id')}] {gap.get('requirement', '')[:150]}"
                )
        
        return "\n".join(context_parts)
    
    def _create_report_prompt(self, compliance_score: float, total_requirements: int, total_gaps: int) -> str:
        """Create prompt for report generation."""
        
        status = "excellent" if compliance_score >= 90 else "good" if compliance_score >= 75 else "fair" if compliance_score >= 60 else "poor"
        
        prompt = f"""
Generate a professional compliance report in Markdown format based on the provided context.

The document has achieved a {compliance_score:.1f}% compliance score, which is considered {status}.
There are {total_requirements} total requirements and {total_gaps} identified gaps.

Structure the report with these sections:

## Executive Summary
Provide a 2-3 paragraph overview of the compliance status, highlighting key findings.

## Compliance Score Analysis
Explain the {compliance_score:.1f}% score with breakdown by requirement categories.

## Compliant Sections
List the requirements that are fully satisfied, organized by category.
Include the similarity scores and brief descriptions.

## Gaps and Deficiencies
Detail the identified gaps organized by severity (High, Medium, Low).
For each gap:
- State the requirement ID and text
- Explain what is missing or insufficient
- Provide the severity level and rationale

## Recommendations
Provide prioritized, actionable steps to address the gaps.
Start with high severity items.
Be specific and practical.

## Conclusion
Summarize the current state and outline next steps to achieve full compliance.

Use professional language suitable for regulatory/audit purposes.
Format all sections with proper Markdown headers, lists, and emphasis.
"""
        return prompt
    
    def _extract_recommendations(self, gaps: List[Dict]) -> List[str]:
        """Extract prioritized recommendations from gaps."""
        
        recommendations = []
        
        # Sort gaps by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        sorted_gaps = sorted(gaps, key=lambda g: severity_order.get(g.get("severity", "low"), 3))
        
        for gap in sorted_gaps[:20]:  # Top 20 recommendations
            recommendation = gap.get("recommendation", "")
            if recommendation and recommendation not in recommendations:
                recommendations.append(recommendation)
        
        return recommendations
    
    def _add_metadata_section(self, report: str, document_id: str, compliance_score: float) -> str:
        """Add metadata header to report."""
        
        metadata = f"""---
report_type: Compliance Analysis Report
document_id: {document_id}
generated_at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
compliance_score: {compliance_score:.1f}%
---

"""
        return metadata + report
    
    def _generate_fallback_report(self, document_id: str, compliance_score: float, gaps: List[Dict]) -> str:
        """Generate simple fallback report if LLM fails."""
        
        high_gaps = [g for g in gaps if g.get("severity") == "high"]
        medium_gaps = [g for g in gaps if g.get("severity") == "medium"]
        low_gaps = [g for g in gaps if g.get("severity") == "low"]
        
        report = f"""# Compliance Report

**Document ID:** {document_id}  
**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Compliance Score:** {compliance_score:.1f}%

## Executive Summary

The document has achieved a compliance score of {compliance_score:.1f}%.

## Identified Gaps

### High Severity ({len(high_gaps)})
"""
        for gap in high_gaps[:10]:
            report += f"\n- **{gap.get('requirement_id')}**: {gap.get('requirement', '')[:200]}\n"
        
        report += f"\n### Medium Severity ({len(medium_gaps)})\n"
        for gap in medium_gaps[:10]:
            report += f"\n- **{gap.get('requirement_id')}**: {gap.get('requirement', '')[:200]}\n"
        
        report += f"\n### Low Severity ({len(low_gaps)})\n"
        for gap in low_gaps[:10]:
            report += f"\n- **{gap.get('requirement_id')}**: {gap.get('requirement', '')[:200]}\n"
        
        report += "\n## Recommendations\n\n"
        for i, gap in enumerate(sorted(gaps, key=lambda g: {"high": 0, "medium": 1, "low": 2}.get(g.get("severity", "low"), 3))[:10], 1):
            report += f"{i}. {gap.get('recommendation', 'Address requirement ' + gap.get('requirement_id', ''))}\n"
        
        return report
