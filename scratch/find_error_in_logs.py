def search_logs():
    log_path = r"c:\Users\shiva\Desktop\AAA\logs\hospital_voice_receptionist.log"
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    print(f"Total lines in log: {len(lines)}")
    
    # Let's search for "shiva" or "naam" in the last 20,000 lines
    search_range = lines[-20000:]
    matches = []
    for idx, line in enumerate(search_range):
        if "shiva" in line.lower() or "naam" in line.lower() or "मेरा" in line or "error" in line.lower() or "exception" in line.lower():
            matches.append(idx)
            
    print(f"Found {len(matches)} matches in the last 20000 lines.")
    
    # Print the last 25 matching blocks with context
    printed_ranges = []
    for idx in matches[-25:]:
        start = max(0, idx - 5)
        end = min(len(search_range), idx + 15)
        
        already_printed = False
        for ps, pe in printed_ranges:
            if start >= ps and end <= pe:
                already_printed = True
                break
        if already_printed:
            continue
            
        printed_ranges.append((start, end))
        print("="*60)
        print(f"Match found around line {idx} in search window (absolute line {len(lines) - 20000 + idx}):")
        for i in range(start, end):
            print(f"{i + len(lines) - 20000}: {search_range[i].strip()}")

if __name__ == "__main__":
    search_logs()
