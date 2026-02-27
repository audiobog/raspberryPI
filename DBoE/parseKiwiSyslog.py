import sys

def extract_unique_hosts(file_path):
    unique_hosts = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Strip whitespace from the ends of the line
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Split the line by tabs (Kiwi usually defaults to tab-delimited)
                # If your file uses spaces instead, change '\t' to None
                parts = line.split('\t')
                
                # Check if the line has enough columns (we need at least 3)
                if len(parts) >= 3:
                    host = parts[2] # Python lists start at 0, so 2 is the 3rd column
                    unique_hosts.add(host)
                    
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return
    except Exception as e:
        print(f"An error occurred: {e}")
        return

    # Print results
    print(f"--- Found {len(unique_hosts)} unique hosts ---")
    for host in sorted(unique_hosts):
        print(host)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_hosts.py <path_to_logfile>")
    else:
        log_file = sys.argv[1]
        extract_unique_hosts(log_file)
