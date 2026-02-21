"""
Gap analysis engine for compliance checking.
Identifies missing and non-compliant sections.
"""

from typing import List, Dict, Tuple
from app.logging_config import get_logger

logger = get_logger(__name__)


class GapAnalyzer:
    """Analyze compliance gaps between document and templates."""
    
    def __init__(self, high_threshold: float = 0.85, medium_threshold: float = 0.75):
        """
        Initialize gap analyzer.
        
        Args:
            high_threshold: Threshold for full compliance
            medium_threshold: Threshold for partial compliance
        """
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        logger.info(f"GapAnalyzer initialized with thresholds: high={high_threshold}, medium={medium_threshold}")
    
    def analyze(
        self,
        matched_sections: List[Dict],
        templates: List[Dict]
    ) -> Tuple[List[Dict], float]:
        """
        Analyze compliance gaps.
        
        Args:
            matched_sections: Matched sections from template matcher
            templates: Original template chunks
        
        Returns:
            Tuple of (gaps, compliance_score)
        """
        try:
            if not matched_sections:
                logger.warning("No matched sections provided for gap analysis")
                return [], 0.0
            
            gaps = []
            total_requirements = len(matched_sections)
            compliant_count = 0
            partial_count = 0
            
            logger.info(f"Analyzing {total_requirements} requirements for gaps")
            
            for section in matched_sections:
                status = section.get("status", "missing")
                score = section.get("similarity_score", 0.0)
                
                if status == "compliant" and score >= self.high_threshold:
                    compliant_count += 1
                elif status == "compliant" and score >= self.medium_threshold:
                    # Weak compliance - add as low severity gap
                    partial_count += 1
                    gaps.append({
                        "requirement_id": section["requirement_id"],
                        "requirement": section["requirement_text"],
                        "category": section.get("requirement_category", "general"),
                        "severity": "low",
                        "gap_type": "weak_compliance",
                        "matched_section": section.get("matched_section"),
                        "similarity_score": score,
                        "recommendation": f"Strengthen alignment with requirement. Current match score: {score:.2f}"
                    })
                elif status == "partial":
                    # Partial match - medium severity
                    partial_count += 1
                    gaps.append({
                        "requirement_id": section["requirement_id"],
                        "requirement": section["requirement_text"],
                        "category": section.get("requirement_category", "general"),
                        "severity": "medium",
                        "gap_type": "partial_compliance",
                        "matched_section": section.get("matched_section"),
                        "similarity_score": score,
                        "recommendation": f"Partially addresses requirement. Add more specific details. Match score: {score:.2f}"
                    })
                else:
                    # Missing or non-compliant - high severity
                    severity = self._calculate_severity(section)
                    gaps.append({
                        "requirement_id": section["requirement_id"],
                        "requirement": section["requirement_text"],
                        "category": section.get("requirement_category", "general"),
                        "severity": severity,
                        "gap_type": "missing",
                        "matched_section": None,
                        "similarity_score": score,
                        "recommendation": self._generate_recommendation(section)
                    })
            
            # Calculate compliance score
            # Full compliance = 100%, partial = 50%, missing = 0%
            weighted_score = (compliant_count * 1.0 + partial_count * 0.5) / total_requirements if total_requirements > 0 else 0
            compliance_score = weighted_score * 100
            
            logger.info(
                f"Gap analysis complete: {compliant_count} compliant, {partial_count} partial, "
                f"{len([g for g in gaps if g['gap_type'] == 'missing'])} missing. Score: {compliance_score:.1f}%"
            )
            
            # Sort gaps by severity
            severity_order = {"high": 0, "medium": 1, "low": 2}
            gaps.sort(key=lambda g: severity_order.get(g["severity"], 3))
            
            return gaps, compliance_score
            
        except Exception as e:
            logger.error(f"Error in gap analysis: {e}", exc_info=True)
            return [], 0.0
    
    def _calculate_severity(self, section: Dict) -> str:
        """
        Calculate gap severity based on requirement language.
        
        Args:
            section: Matched section dictionary
        
        Returns:
            Severity level: "high", "medium", or "low"
        """
        req_text = section.get("requirement_text", "").lower()
        
        # Critical keywords indicate high severity
        critical_keywords = ["must", "shall", "required", "mandatory", "critical", "essential"]
        if any(keyword in req_text for keyword in critical_keywords):
            return "high"
        
        # Recommended keywords indicate medium severity
        recommended_keywords = ["should", "recommended", "advised", "suggested"]
        if any(keyword in req_text for keyword in recommended_keywords):
            return "medium"
        
        # Default to low severity
        return "low"
    
    def _generate_recommendation(self, section: Dict) -> str:
        """
        Generate actionable recommendation for addressing gap.
        
        Args:
            section: Matched section dictionary
        
        Returns:
            Recommendation text
        """
        req_text = section.get("requirement_text", "")
        category = section.get("requirement_category", "general")
        
        # Truncate long requirements for recommendation
        req_preview = req_text[:150] + "..." if len(req_text) > 150 else req_text
        
        return f"Add section addressing requirement in category '{category}': {req_preview}"
    
    def categorize_gaps(self, gaps: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize gaps by severity and type.
        
        Args:
            gaps: List of gap dictionaries
        
        Returns:
            Dictionary mapping categories to gaps
        """
        categorized = {
            "high_severity": [],
            "medium_severity": [],
            "low_severity": [],
            "by_category": {}
        }
        
        for gap in gaps:
            severity = gap.get("severity", "low")
            category = gap.get("category", "general")
            
            # By severity
            if severity == "high":
                categorized["high_severity"].append(gap)
            elif severity == "medium":
                categorized["medium_severity"].append(gap)
            else:
                categorized["low_severity"].append(gap)
            
            # By requirement category
            if category not in categorized["by_category"]:
                categorized["by_category"][category] = []
            categorized["by_category"][category].append(gap)
        
        return categorized
