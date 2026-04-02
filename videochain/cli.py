import cv2
import time
from .vision import VisionEngine
from .rag import RAGEngine

def main():
    print("🚀 VideoChain Multipurpose RAG Initializing...")
    
    # Paths (Assumes you are running from project root)
    vision = VisionEngine(model_path="models/videochain_vision.pth", class_path="models/classes.txt")
    rag = RAGEngine(mode="Security")

    cap = cv2.VideoCapture(0) # Change to filename if needed
    last_alert = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        label, conf = vision.predict(frame)
        
        # Logic: Only trigger RAG for non-normal actions every 5 seconds
        if label != "normal" and (time.time() - last_alert > 5):
            alert = rag.generate_alert(label)
            print(f"🚨 [AI ALERT]: {alert}")
            last_alert = time.time()

        # UI Overlay
        color = (0, 255, 0) if label == "normal" else (0, 0, 255)
        cv2.putText(frame, f"{label.upper()} ({conf:.1f}%)", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.imshow("VideoChain Live Installer Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()