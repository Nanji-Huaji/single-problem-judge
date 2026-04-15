import sys

def flush_print(msg):
    print(msg)
    sys.stdout.flush()

def main():
    # Read initial map, 20 lines
    try:
        board = []
        for _ in range(20):
            line = input().strip()
            board.append(line)
        
        # Read N
        n_str = input().strip()
        n = int(n_str)
        
        score = 0
        direction = 'W'
        
        while True:
            # We want to output our move
            # For this simple bot, we'll just constantly try to move W (up).
            # This means we will soon crash into the wall.
            flush_print(direction)
            flush_print(str(score))
            
            # Read interactive response
            # Format: either "row col" or "20 20" or "100 100"
            resp = input().strip()
            if resp == "100 100":
                # Game over, output final map and score
                for row in board:
                    flush_print(row)
                flush_print(str(score))
                break
            elif resp == "20 20":
                pass # nothing happened
            else:
                # new food spawned (row col)
                parts = resp.split()
                if len(parts) == 2:
                    score += 10
                    
    except EOFError:
        pass

if __name__ == "__main__":
    main()
