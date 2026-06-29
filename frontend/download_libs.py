import os
import urllib.request
import logging

logger = logging.getLogger(__name__)

LIBS = {
    "react.production.min.js": "https://unpkg.com/react@18.2.0/umd/react.production.min.js",
    "react-dom.production.min.js": "https://unpkg.com/react-dom@18.2.0/umd/react-dom.production.min.js",
    "plotly.min.js": "https://cdn.plot.ly/plotly-2.24.1.min.js",
    "tailwind.min.js": "https://cdn.tailwindcss.com/3.3.0"
}

def main():
    dest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static/js")
    os.makedirs(dest_dir, exist_ok=True)
    
    print("Downloading offline web frontend libraries...")
    for filename, url in LIBS.items():
        filepath = os.path.join(dest_dir, filename)
        if os.path.exists(filepath):
            print(f"Already downloaded: {filename}")
            continue
        try:
            print(f"Downloading {filename} from {url}...")
            # Set agent header
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            
            urllib.request.urlretrieve(url, filepath)
            print(f"Success: {filename}")
        except Exception as e:
            print(f"Failed to download {filename}: {e}")

if __name__ == "__main__":
    main()
