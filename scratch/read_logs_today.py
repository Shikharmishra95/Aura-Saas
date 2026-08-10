import sys

def read_today():
    # Configure stdout to use UTF-8
    sys.stdout.reconfigure(encoding='utf-8')
    log_path = r"c:\Users\shiva\Desktop\AAA\logs\hospital_voice_receptionist.log"
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        
    print(f"Total lines: {len(lines)}")
    # Print the last 300 lines
    print("="*40 + " LAST 300 LINES " + "="*40)
    for line in lines[-300:]:
        print(line.strip())

if __name__ == "__main__":
    read_today()
