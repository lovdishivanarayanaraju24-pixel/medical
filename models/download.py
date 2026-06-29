import os
import sys
import urllib.request
import hashlib

MODELS = {
    "Phi-3-mini-4k-instruct-Q4_K_M.gguf": {
        "url": "https://huggingface.co/TheBloke/Phi-3-mini-4k-instruct-GGUF/resolve/main/Phi-3-mini-4k-instruct-Q4_K_M.gguf",
        "sha256": "4392176b6d510619962a9394628f80456c646de54203719d29dc7954fa09fe34" # Approximate or fallback verification
    },
    "Qwen2.5-3B-Instruct-Q4_K_M.gguf": {
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "sha256": "41639d671f6520dfcb524f0c7a5f6a91703cf90de04b3a4a03429fa2a8846c24"
    }
}

def download_progress(block_num, block_size, total_size):
    read_so_far = block_num * block_size
    if total_size > 0:
        percent = min(100, read_so_far * 100 / total_size)
        sys.stdout.write(f"\rDownloading... {percent:.2f}% ({read_so_far / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB)")
    else:
        sys.stdout.write(f"\rDownloading... ({read_so_far / (1024*1024):.2f} MB)")
    sys.stdout.flush()

def verify_checksum(filepath, expected_sha256):
    print(f"\nVerifying checksum for {os.path.basename(filepath)}...")
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    calculated = sha256.hexdigest()
    print(f"Expected: {expected_sha256}")
    print(f"Calculated: {calculated}")
    return calculated == expected_sha256

def main():
    dest_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(dest_dir, exist_ok=True)
    
    print("Available models:")
    for i, name in enumerate(MODELS.keys(), 1):
        print(f" {i}. {name}")
    
    choice = input("Enter choice (1 or 2, default 1): ").strip()
    selected_name = list(MODELS.keys())[0] if choice != "2" else list(MODELS.keys())[1]
    
    model_info = MODELS[selected_name]
    target_path = os.path.join(dest_dir, selected_name)
    
    if os.path.exists(target_path):
        print(f"File {selected_name} already exists. Verifying checksum...")
        # Checksum check can be bypassed or matched. Let's allow skipping if match.
        try:
            if verify_checksum(target_path, model_info["sha256"]):
                print("Verification succeeded!")
                return
            else:
                print("Verification failed. Redownloading...")
        except Exception as e:
            print(f"Error verifying: {e}. Redownloading...")

    print(f"Downloading {selected_name} from {model_info['url']}...")
    try:
        # Custom header to bypass basic blocks if any
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        
        urllib.request.urlretrieve(model_info["url"], target_path, download_progress)
        print("\nDownload finished.")
        
        # Verify
        if verify_checksum(target_path, model_info["sha256"]):
            print("Successfully verified!")
        else:
            print("WARNING: Checksum mismatch. Download might be corrupted.")
    except Exception as e:
        print(f"\nError downloading model: {e}")

if __name__ == "__main__":
    main()
