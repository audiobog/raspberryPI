import sys
from neo4j import GraphDatabase

# --- CONFIGURATION ---
NEO4J_URI = "bolt://localhost:7687" # Update if remote
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "SurreHue12#"
# ---------------------

def extract_and_load(file_path):
    unique_hosts = set()
    
    # 1. Extract Hosts (Same logic as before)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split('\t') # Change to .split() if space-delimited
                if len(parts) >= 3:
                    unique_hosts.add(parts[2])
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"Found {len(unique_hosts)} unique hosts. Connecting to Neo4j...")

    # 2. Connect to Neo4j and Load Data
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            # We pass the list of hosts to a single query for efficiency
            session.write_transaction(create_nodes, list(unique_hosts))
            
        driver.close()
        print("Successfully imported hosts into Neo4j!")
        
    except Exception as e:
        print(f"Database Error: {e}")

def create_nodes(tx, host_list):
    query = """
    UNWIND $hosts AS hostname
    MERGE (h:Host {name: hostname})
    ON CREATE SET h.created = date(), h.source_syslog = true
    ON MATCH SET h.last_seen_syslog = date(), h.status = 'verified'
    SET h:SyslogHost
    """
    tx.run(query, hosts=host_list)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 import_hosts.py <path_to_logfile>")
    else:
        extract_and_load(sys.argv[1])
