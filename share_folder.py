import os
import socket
import sys
import http.server
import socketserver
import subprocess
import argparse

def get_local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.168.0.1", 80))
            return s.getsockname()[0]
        except Exception:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)

def generate_qr_code(url):
    try:
        subprocess.run(["qrencode", "-t", "ANSIUTF8", url], check=True)
    except FileNotFoundError:
        print("Error: qrencode not found. Install it with 'sudo apt install qrencode'.")

def share_file_or_folder(path, port=3000):
    if not os.path.exists(path):
        print(f"Error: Path '{path}' does not exist.")
        sys.exit(1)

    abs_path = os.path.abspath(path)
    if os.path.isfile(abs_path):
        directory, file_name = os.path.split(abs_path)
    elif os.path.isdir(abs_path):
        directory = abs_path
        file_name = None
    else:
        print(f"Error: '{path}' is neither a file nor a directory.")
        sys.exit(1)

    os.chdir(directory)
    ip_address = get_local_ip()
    url = f"http://{ip_address}:{port}/{file_name or ''}"

    print(f"Sharing '{path}' at {url}")
    generate_qr_code(url)
    print("Press Ctrl+C to stop the server.")

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    handler = http.server.SimpleHTTPRequestHandler
    try:
        with ReusableTCPServer(("0.0.0.0", port), handler) as httpd:
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 98:
            print(f"Error: Port {port} is already in use. Please try a different port.")
        else:
            raise
    except KeyboardInterrupt:
        print("\nServer stopped.")

def main():
    parser = argparse.ArgumentParser(description="Share files or folders over the local network with an HTTP server and QR code.")
    parser.add_argument("path", help="Path to the file or folder to share.")
    parser.add_argument("-p", "--port", type=int, default=3000, help="Port to run the HTTP server (default: 3000).")

    args = parser.parse_args()

    abs_path = os.path.abspath(args.path.strip())
    share_file_or_folder(abs_path, args.port)

if __name__ == "__main__":
    main()