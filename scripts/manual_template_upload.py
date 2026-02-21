#!/usr/bin/env python3
"""
Manual template upload script.
Run this in Cloud Shell to manually process and upload a template.
"""

import sys
import json
import uuid
from datetime import datetime

# Template content (ISO 27001)
TEMPLATE_CONTENT = """
ISO 27001:2022 Compliance Requirements Template

SECTION 1: INFORMATION SECURITY POLICIES
1.1 Policies for information security
- Management shall define, approve, publish, communicate, and review information security policies
- Policies shall be reviewed at planned intervals or if significant changes occur
- Information security policies shall be communicated to employees and relevant external parties

1.2 Review of the policies for information security
- Policies shall be reviewed at planned intervals
- Reviews shall ensure continuing suitability, adequacy, and effectiveness

SECTION 2: ORGANIZATION OF INFORMATION SECURITY
2.1 Internal organization
- Management responsibility for information security shall be defined and allocated
- Conflicting duties and areas of responsibility shall be segregated
- Contact with authorities shall be maintained
- Contact with special interest groups shall be maintained

2.2 Mobile devices and teleworking
- Policy and supporting security measures shall be adopted for mobile devices
- Policy and supporting security measures shall be implemented for teleworking

SECTION 3: HUMAN RESOURCE SECURITY
3.1 Prior to employment
- Background verification checks on all candidates for employment shall be carried out
- Employees and contractors shall agree and sign the terms and conditions of their employment contract

3.2 During employment
- Management shall require employees and contractors to apply information security in accordance with policies
- All employees shall receive appropriate awareness education and training
- A formal disciplinary process shall be established for employees who have committed a security breach

3.3 Termination and change of employment
- Information security responsibilities and duties that remain valid after termination shall be defined and enforced
- Return of all organizational assets shall be ensured

SECTION 4: ASSET MANAGEMENT
4.1 Responsibility for assets
- Assets associated with information and information processing facilities shall be identified
- An inventory of assets shall be drawn up and maintained
- Assets maintained in the inventory shall be owned
- Acceptable use of information and assets shall be identified, documented, and implemented

4.2 Information classification
- Information shall be classified in terms of legal requirements, value, criticality, and sensitivity
- Appropriate set of procedures for information labeling shall be developed
- Procedures for handling assets shall be developed in accordance with the information classification

4.3 Media handling
- Procedures shall be implemented for the management of removable media
- Media shall be disposed of securely when no longer required
- Media containing information shall be protected against unauthorized access

SECTION 5: ACCESS CONTROL
5.1 Business requirements of access control
- Access control policy shall be established, documented, and reviewed
- Users shall only be provided with access to services that they have been authorized to use

5.2 User access management
- Formal user registration and de-registration process shall be implemented
- Formal user access provisioning process shall be implemented
- Management of privileged access rights shall be restricted and controlled
- Secret authentication information shall be allocated through a formal management process
- Access rights shall be reviewed at regular intervals

5.3 User responsibilities
- Users shall be required to follow the organization's practices in the use of secret authentication information

5.4 System and application access control
- Access to information and application system functions shall be restricted
- Where required by the access control policy, access to systems and applications shall be controlled by a secure log-on procedure
- Password management systems shall be interactive and ensure quality passwords
- Use of utility programs that might be capable of overriding system and application controls shall be restricted

SECTION 6: CRYPTOGRAPHY
6.1 Cryptographic controls
- Policy on the use of cryptographic controls shall be developed and implemented
- Policy on the use, protection, and lifetime of cryptographic keys shall be developed
"""

def main():
    print("=" * 80)
    print("Manual Template Upload Script")
    print("=" * 80)
    
    # Configuration (UPDATE THESE VALUES)
    PROJECT_ID = "btoproject-486405-486604"
    REGION = "us-central1"
    
    print(f"\nProject ID: {PROJECT_ID}")
    print(f"Region: {REGION}")
    
    try:
        # Import required libraries
        print("\nImporting libraries...")
        from google.cloud import firestore
        from google.cloud import aiplatform
        import vertexai
        from vertexai.language_models import TextEmbeddingModel
        
        # Initialize services
        print("Initializing services...")
        db = firestore.Client(project=PROJECT_ID)
        vertexai.init(project=PROJECT_ID, location=REGION)
        
        # Generate template ID
        template_id = str(uuid.uuid4())
        print(f"\nTemplate ID: {template_id}")
        
        # Chunk the template
        print("\nChunking template...")
        lines = TEMPLATE_CONTENT.strip().split('\n\n')
        chunks = []
        for i, section in enumerate(lines):
            if section.strip():
                chunks.append({
                    'text': section.strip(),
                    'chunk_id': f"{template_id}_{i}",
                    'template_id': template_id,
                    'chunk_index': i
                })
        
        print(f"Created {len(chunks)} chunks")
        
        # Generate embeddings
        print("\nGenerating embeddings...")
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        texts = [chunk['text'] for chunk in chunks]
        
        embeddings_batch = model.get_embeddings(texts)
        embeddings = [emb.values for emb in embeddings_batch]
        
        print(f"Generated {len(embeddings)} embeddings")
        
        # Store in Firestore
        print("\nStoring in Firestore...")
        
        # Store template metadata
        template_ref = db.collection('compliance_templates').document(template_id)
        template_ref.set({
            'template_id': template_id,
            'template_type': 'ISO27001',
            'version': '2022',
            'status': 'ready',
            'chunk_count': len(chunks),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        print(f"  ✓ Template metadata stored")
        
        # Store chunks
        for i, chunk in enumerate(chunks):
            chunk_ref = db.collection('compliance_template_chunks').document(chunk['chunk_id'])
            chunk_data = {
                'chunk_id': chunk['chunk_id'],
                'template_id': template_id,
                'template_type': 'ISO27001',
                'text': chunk['text'],
                'chunk_index': chunk['chunk_index'],
                'embedding': embeddings[i],
                'created_at': datetime.utcnow()
            }
            chunk_ref.set(chunk_data)
        
        print(f"  ✓ {len(chunks)} chunks stored in Firestore")
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ Template Upload Successful!")
        print("=" * 80)
        print(f"Template ID: {template_id}")
        print(f"Template Type: ISO27001")
        print(f"Chunks: {len(chunks)}")
        print(f"Embeddings: {len(embeddings)}")
        print("\nFirestore Collections Updated:")
        print(f"  - compliance_templates/{template_id}")
        print(f"  - compliance_template_chunks (x{len(chunks)})")
        
        print("\n✨ Template is now ready for compliance checking!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
