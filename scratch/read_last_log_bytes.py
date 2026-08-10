import sys

def get_recent_tracebacks():
    log_path = r"c:\Users\shiva\Desktop\AAA\logs\hospital_voice_receptionist.log"
    with open(log_path, "rb") as f:
        # Seek to the end minus 1MB
        try:
            f.seek(-1000000, 2)
        except OSError:
            pass # File is smaller than 1MB
        content = f.read().decode("utf-8", errors="ignore")
        
    lines = content.splitlines()
    print(f"Total lines in last segment: {len(lines)}")
    
    # We want to print any blocks starting with Traceback (most recent call last)
    in_traceback = False
    traceback_block = []
    
    for line in lines:
        if "Traceback (most recent call last)" in line:
            in_traceback = True
            traceback_block = [line]
        elif in_traceback:
            traceback_block.append(line)
            # Tracebacks usually end when a line doesn't start with space, but wait, the last line is the exception description
            # Let's stop if we see a line that doesn't start with space/tab and doesn't contain "File " or "line " (excluding the first line)
            if len(traceback_block) > 1 and not line.startswith(" ") and not line.startswith("\t") and "File " not in line:
                in_traceback = False
                print("="*80)
                print("\n".join(traceback_block))
                print("="*80)
                traceback_block = []

if __name__ == "__main__":
    get_recent_tracebacks()
