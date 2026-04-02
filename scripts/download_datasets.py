import os
import zipfile
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

def setup_multipurpose_datasets():
    # 1. Initialize API
    print("🔐 Authenticating with Kaggle API...")
    try:
        api = KaggleApi()
        api.authenticate()
    except Exception as e:
        print(f"❌ Authentication Failed: {e}")
        return

    # 2. The "Verified" Suite (Swapped dead links for live ones)
    datasets = {
        # High quality CCTV postures (Walk, Run, Fall) - YOU ALREADY HAVE THIS
        "jonathannield/cctv-action-recognition-dataset": "cctv_actions",
        
        # General Human Actions (Calling, Eating, Running) - VERY STABLE
        "anthonymanoel/human-action-recognition": "human_activities",
        
        # Surveillance-specific actions (Frames extracted) - COMPACT
        "vbookshelf/vgg16-human-action-recognition": "surveillance_frames"
    }
    
    base_data_path = Path("data/raw")
    base_data_path.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Data Acquisition started at: {base_data_path.absolute()}")

    for slug, folder_name in datasets.items():
        target_path = base_data_path / folder_name
        
        if target_path.exists() and any(target_path.iterdir()):
            print(f"⏩ Skipping {folder_name}: Data already present.")
            continue

        print(f"\n📦 Fetching {slug}...")
        
        try:
            # Programmatic download and unzip
            api.dataset_download_files(slug, path=str(base_data_path), unzip=True)
            print(f"✅ Successfully acquired: {folder_name}")

        except Exception as e:
            print(f"⚠️ Could not fetch {slug}. Error: {e}")
            print("💡 Don't worry, move to the next one. We only need two for a solid model.")

    print("\n✨ Ingestion Complete! Check 'data/raw' for your folders.")

if __name__ == "__main__":
    setup_multipurpose_datasets()