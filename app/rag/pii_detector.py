"""
PII Detection using Google Cloud Data Loss Prevention (DLP) API
Scans text for sensitive information before storing in Vector Search
"""

from typing import List, Dict, Optional
from google.cloud import dlp_v2
import logging

logger = logging.getLogger(__name__)


class PIIDetector:
    """
    Detects and classifies PII in text using Cloud DLP
    """
    
    def __init__(self, project_id: str):
        """
        Initialize PII detector with Cloud DLP client
        
        Args:
            project_id: GCP project ID
        """
        self.project_id = project_id
        try:
            self.dlp_client = dlp_v2.DlpServiceClient()
            self.parent = f"projects/{project_id}"
            logger.info(f" Cloud DLP client initialized successfully for project: {project_id}")
            # Test the client
            test_result = self.detect_pii("test@example.com")
            logger.info(f" Cloud DLP test successful - detected PII: {test_result['has_pii']}")
        except Exception as e:
            logger.error(f" Could not initialize Cloud DLP: {e}. PII detection disabled.")
            self.dlp_client = None
    
    def detect_pii(self, text: str, info_types: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Detect PII in text using Cloud DLP
        
        Args:
            text: Text to scan for PII
            info_types: List of info types to detect (e.g., EMAIL_ADDRESS, PHONE_NUMBER)
                       If None, uses default comprehensive list
        
        Returns:
            Dict with:
                - has_pii: bool - Whether PII was found
                - pii_types: List[str] - Types of PII found
                - pii_count: int - Number of PII instances
                - likelihood: str - Overall likelihood rating
                - status: str - "clean", "low_risk", "high_risk", "blocked"
        """
        if not self.dlp_client:
            # Fallback when DLP is not available
            logger.warning(" PII detection skipped - DLP client not initialized")
            return {
                "has_pii": False,
                "pii_types": [],
                "pii_count": 0,
                "likelihood": "UNKNOWN",
                "status": "clean"
            }
        
        # Default comprehensive PII types
        if info_types is None:
            info_types = [
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "CREDIT_CARD_NUMBER",
                "PERSON_NAME",
                "US_SOCIAL_SECURITY_NUMBER",
                "IP_ADDRESS",
                "PASSPORT",
                "DATE_OF_BIRTH",
                "STREET_ADDRESS",
                "MEDICAL_RECORD_NUMBER",
                "FINANCIAL_ACCOUNT_NUMBER",
            ]
        
        # Configure inspection
        inspect_config = {
            "info_types": [{"name": info_type} for info_type in info_types],
            "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
            "include_quote": False,  # Don't return the actual PII values
        }
        
        # Create inspection request
        item = {"value": text}
        
        try:
            response = self.dlp_client.inspect_content(
                request={
                    "parent": self.parent,
                    "inspect_config": inspect_config,
                    "item": item,
                }
            )
            
            # Analyze findings
            findings = response.result.findings
            pii_types_found = list(set([finding.info_type.name for finding in findings]))
            pii_count = len(findings)
            
            if pii_count > 0:
                logger.warning(f" PII DETECTED: {pii_count} instances of types: {pii_types_found}")
            
            # Determine overall likelihood
            max_likelihood = dlp_v2.Likelihood.LIKELIHOOD_UNSPECIFIED
            for finding in findings:
                if finding.likelihood > max_likelihood:
                    max_likelihood = finding.likelihood
            
            # Determine status based on findings
            status = self._determine_status(pii_count, max_likelihood)
            
            return {
                "has_pii": pii_count > 0,
                "pii_types": pii_types_found,
                "pii_count": pii_count,
                "likelihood": dlp_v2.Likelihood(max_likelihood).name,
                "status": status
            }
            
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
            return {
                "has_pii": False,
                "pii_types": [],
                "pii_count": 0,
                "likelihood": "ERROR",
                "status": "clean"  # Fail open in case of errors
            }
    
    def _determine_status(self, pii_count: int, max_likelihood: int) -> str:
        """
        Determine document status based on PII findings
        
        Returns:
            - "clean": No PII found
            - "low_risk": PII found but low confidence or low sensitivity
            - "high_risk": High confidence PII found
            - "blocked": Critical PII that should never be stored
        """
        if pii_count == 0:
            return "clean"
        
        # Map DLP likelihood to status
        if max_likelihood >= dlp_v2.Likelihood.VERY_LIKELY:
            return "high_risk"
        elif max_likelihood >= dlp_v2.Likelihood.LIKELY:
            return "high_risk"
        elif max_likelihood >= dlp_v2.Likelihood.POSSIBLE:
            return "low_risk"
        else:
            return "clean"
    
    def redact_pii(self, text: str, info_types: Optional[List[str]] = None) -> str:
        """
        Redact PII in text by replacing with [REDACTED]
        
        Args:
            text: Text to redact
            info_types: Specific PII types to redact (default: all)
        
        Returns:
            Text with PII redacted
        """
        if not self.dlp_client:
            logger.warning("⚠ PII redaction skipped - DLP client not initialized")
            return text
        
        # Default comprehensive PII types
        if info_types is None:
            info_types = [
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "CREDIT_CARD_NUMBER",
                "PERSON_NAME",
                "US_SOCIAL_SECURITY_NUMBER",
                "IP_ADDRESS",
                "PASSPORT",
                "DATE_OF_BIRTH",
                "STREET_ADDRESS",
                "MEDICAL_RECORD_NUMBER",
                "FINANCIAL_ACCOUNT_NUMBER",
            ]
        
        # Configure deidentification
        inspect_config = {
            "info_types": [{"name": info_type} for info_type in info_types],
            "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
        }
        
        # Redact PII by replacing with placeholder
        deidentify_config = {
            "info_type_transformations": {
                "transformations": [
                    {
                        "primitive_transformation": {
                            "replace_config": {
                                "new_value": {"string_value": "[REDACTED]"}
                            }
                        }
                    }
                ]
            }
        }
        
        item = {"value": text}
        
        try:
            response = self.dlp_client.deidentify_content(
                request={
                    "parent": self.parent,
                    "deidentify_config": deidentify_config,
                    "inspect_config": inspect_config,
                    "item": item,
                }
            )
            
            redacted_text = response.item.value
            logger.info(f"🔒 PII redacted from text (original length: {len(text)}, redacted: {len(redacted_text)})")
            return redacted_text
            
        except Exception as e:
            logger.error(f" PII redaction failed: {e}")
            # Return original text if redaction fails (fail open)
            return text
    

    

