import os
import urllib.request

def main():
    dest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static/js")
    os.makedirs(dest_dir, exist_ok=True)
    url = "https://unpkg.com/@babel/standalone@7.22.9/babel.min.js"
    filepath = os.path.join(dest_dir, "babel.min.js")
    
    if os.path.exists(filepath):
        print("Babel already downloaded.")
        return
        
    print("Downloading Babel...")
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url, filepath)
    print("Babel downloaded successfully.")

if __name__ == "__main__":
    main()
