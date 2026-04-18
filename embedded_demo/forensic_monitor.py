"""
embedded_demo/forensic_monitor.py
---------------------------------
Advanced "Real-Life" Application Demo.
This script demonstrates how to embed VidChain as a library into a 
standalone security investigation tool.

Use Case: Corporate Forensic Audit
1. Ingests a surveillance log.
2. Automatically identifies suspicious entities.
3. Performs GraphRAG multi-hop lookups.
4. Generates a professional forensic report in Markdown.
"""

import os
import sys
from datetime import datetime

# Import the VidChain framework
try:
    from vidchain import VidChain
except ImportError:
    print("Error: 'vidchain' library not found.")
    print("To run this demo, please install the framework first:")
    print("  pip install -e .")
    sys.exit(1)


class ForensicAuditAgent:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.report_name = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        # Initialize VidChain in 'Forensic' mode
        print(f"[*] Initializing Stark-Tech Intelligence Engine...")
        self.vc = VidChain(verbose=True)

    def run_audit(self):
        print(f"[*] Starting Neural Analysis on feed: {self.video_path}")
        
        # 1. Ingest the video log
        self.vc.ingest(self.video_path)
        
        # 2. Automated Forensic Queries
        print(f"[*] Extracting Intelligence via GraphRAG...")
        
        # Query 1: The Narrative Story
        summary = self.vc.ask("Provide a full chronological narrative of events in this video.")
        
        # Query 2: Entity Cross-Reference
        entities = self.vc.ask("List every person and object identified. For each, tell me when they were first seen and if they interacted with any other objects.")
        
        # Query 3: Specific Security Audit (OCR + Action)
        security_audit = self.vc.ask(
            "Security Audit: Were there any 'SUSPICIOUS' actions detected? "
            "Also, detail every brand name or specific text (OCR) visible on screens or objects."
        )

        # 3. Generate the Report
        self._generate_markdown_report(summary, entities, security_audit)
        print(f"[!] Audit Complete! Report generated: {self.report_name}")

    def _generate_markdown_report(self, summary, entities, security):
        report_content = f"""# 🛡️ VIDCHAIN FORENSIC AUDIT REPORT
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Source Feed:** `{os.path.abspath(self.video_path)}`

---

## 📖 1. Event Narrative (B.A.B.U.R.A.O. Summary)
{summary}

---

## 🔍 2. Entity Intelligence (GraphRAG Tracking)
{entities}

---

## ⚠️ 3. Security & Compliance (OCR / Actions)
{security}

---

## 🛠️ Technical Metadata
- **Engine:** VidChain v0.6.0 (Modular VLM Pipeline)
- **Intelligence Model:** Ollama/Moondream
- **Forensic Index:** ChromaDB + NetworkX GraphRAG
"""
        with open(self.report_name, "w", encoding="utf-8") as f:
            f.write(report_content)


if __name__ == "__main__":
    # Point to a local video file
    target_video = "sample.mp4" 
    
    if not os.path.exists(target_video):
        print(f"Error: Could not find {target_video} to analyze.")
        print("Please place a video file named 'sample.mp4' in the project root.")
    else:
        agent = ForensicAuditAgent(target_video)
        agent.run_audit()
