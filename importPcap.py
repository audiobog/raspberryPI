import os
import sys
from collections import defaultdict
from datetime import datetime

# Scapy for PCAP parsing
try:
    from scapy.all import PcapReader, IP, TCP, UDP, ICMP
    from scapy.data import IP_PROTOS, TCP_SERVICES, UDP_SERVICES
except ImportError:
    print("Scapy not found. Please install it with: pip install scapy")
    sys.exit(1)

# Neo4j driver
try:
    from neo4j import GraphDatabase, basic_auth
except ImportError:
    print("Neo4j driver not found. Please install it with: pip install neo4j")
    sys.exit(1)

# --- Configuration ---
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "SurreHue12#" # IMPORTANT: Change this in a real environment!
PCAP_FILE_PATH = "ultimate_wireshark_protocols_pcap_220213.pcap" # Path to your downloaded PCAP file

# --- Helper Functions ---
def get_protocol_name(proto_num, dest_port=None):
    """Maps IP protocol number to a human-readable name, and port to service name."""
    # First, try to get IP protocol name
    proto_name = IP_PROTOS.get(proto_num, f"UNKNOWN_IP_PROTO_{proto_num}")

    # If it's TCP or UDP, try to get the service name from the port
    if dest_port:
        if proto_num == 6: # TCP
            service_name = TCP_SERVICES.get(dest_port)
            if service_name:
                return service_name.upper() # e.g., HTTP, HTTPS
        elif proto_num == 17: # UDP
            service_name = UDP_SERVICES.get(dest_port)
            if service_name:
                return service_name.upper() # e.g., DNS, NTP
    
    return proto_name

def parse_pcap_and_aggregate_connections(pcap_path):
    """
    Parses a PCAP file and aggregates connection details.
    Returns a dictionary: {(src_ip, dst_ip, protocol_name, dest_port): packet_count}
    """
    if not os.path.exists(pcap_path):
        print(f"Error: PCAP file not found at {pcap_path}")
        sys.exit(1)

    print(f"Parsing PCAP file: {pcap_path}...")
    connections = defaultdict(lambda: {'count': 0, 'first_seen': None, 'last_seen': None})
    
    packet_count = 0
    try:
        # Use PcapReader for memory efficiency
        for packet in PcapReader(pcap_path):
            packet_count += 1
            if IP in packet:
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst
                proto_num = packet[IP].proto
                dest_port = None
                
                if TCP in packet:
                    dest_port = packet[TCP].dport
                elif UDP in packet:
                    dest_port = packet[UDP].dport
                elif ICMP in packet:
                    # ICMP doesn't use ports in the same way, we'll represent it as 0
                    dest_port = 0 
                else:
                    # For other IP protocols (e.g., OSPF, GRE) without TCP/UDP/ICMP
                    dest_port = 0 # No specific port for these

                protocol_name = get_protocol_name(proto_num, dest_port)
                
                connection_key = (src_ip, dst_ip, protocol_name, dest_port)
                
                # Update connection details
                current_time = datetime.now() # Using current script time for simplicity, could parse packet timestamp
                if connections[connection_key]['first_seen'] is None:
                    connections[connection_key]['first_seen'] = current_time
                connections[connection_key]['last_seen'] = current_time
                connections[connection_key]['count'] += 1

            if packet_count % 1000 == 0:
                print(f"  Processed {packet_count} packets...", end='\r')

    except Exception as e:
        print(f"\nError processing PCAP file: {e}")
        sys.exit(1)

    print(f"\nFinished parsing. Total packets processed: {packet_count}.")
    print(f"Found {len(connections)} unique connections.")
    return connections

def ingest_to_neo4j(connections_data):
    """
    Connects to Neo4j and ingests the aggregated connection data.
    """
    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    driver = None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USERNAME, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("Neo4j connection successful.")

        # Create an index for faster lookups on Asset nodes
        with driver.session() as session:
            session.run("CREATE CONSTRAINT ON (a:Asset) ASSERT a.ip_address IS UNIQUE")
            print("Ensured uniqueness constraint on Asset.ip_address.")

            # Ingest connections in batches
            batch_size = 1000
            connection_list = list(connections_data.items()) # Convert to list for batching
            
            for i in range(0, len(connection_list), batch_size):
                batch = connection_list[i : i + batch_size]
                
                # Prepare parameters for the Cypher query
                params = []
                for (src_ip, dst_ip, protocol, dest_port), data in batch:
                    params.append({
                        "src_ip": src_ip,
                        "dst_ip": dst_ip,
                        "protocol": protocol,
                        "dest_port": dest_port,
                        "packet_count": data['count'],
                        "first_seen": data['first_seen'].isoformat(),
                        "last_seen": data['last_seen'].isoformat()
                    })

                # Cypher query for MERGE operations
                # MERGE creates if not exists, MATCH finds if exists
                # This ensures assets and relationships are unique based on their identifiers
                query = """
                UNWIND $props AS p
                MERGE (src:Asset {ip_address: p.src_ip})
                MERGE (dst:Asset {ip_address: p.dst_ip})
                MERGE (src)-[r:COMMUNICATES_ON {
                    protocol: p.protocol, 
                    dest_port: p.dest_port
                }]->(dst)
                ON CREATE SET r.initial_packet_count = p.packet_count,
                              r.first_seen = p.first_seen,
                              r.last_seen = p.last_seen
                ON MATCH SET r.total_packet_count = COALESCE(r.total_packet_count, r.initial_packet_count) + p.packet_count,
                             r.last_seen = p.last_seen
                """
                # Note: `COALESCE(r.total_packet_count, r.initial_packet_count)` is crucial
                # if you expect to run this script multiple times on different pcap files
                # and want to accumulate packet counts. If you only run it once per pcap
                # and treat it as the definitive count for that pcap, `r.packet_count = p.packet_count`
                # on both CREATE and MATCH would be simpler.

                session.run(query, props=params)
                print(f"  Ingested {min(i + batch_size, len(connection_list))} / {len(connection_list)} connections...", end='\r')
            
            print(f"\nSuccessfully ingested {len(connections_data)} unique connections into Neo4j.")

    except Exception as e:
        print(f"\nError connecting to or ingesting into Neo4j: {e}")
    finally:
        if driver:
            driver.close()

# --- Main Execution ---
if __name__ == "__main__":
    if not os.path.exists(PCAP_FILE_PATH):
        print(f"ERROR: PCAP file not found at '{PCAP_FILE_PATH}'.")
        print("Please download a test PCAP file (e.g., from wireshark.org/samplecaptures) and place it in the same directory, or update PCAP_FILE_PATH.")
        sys.exit(1)

    aggregated_connections = parse_pcap_and_aggregate_connections(PCAP_FILE_PATH)
    if aggregated_connections:
        ingest_to_neo4j(aggregated_connections)
    else:
        print("No connections found in PCAP to ingest.")
