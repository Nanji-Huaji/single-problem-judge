import sys
import random
import subprocess
import json

def main():
    if len(sys.argv) < 4:
        sys.stderr.write("Usage: python3 interactor.py <N> <seed> <cmd>...\n")
        sys.exit(1)
    
    n = int(sys.argv[1])
    seed = int(sys.argv[2])
    cmd = ' '.join(sys.argv[3:])
    
    random.seed(seed)
    
    board = [['.' for _ in range(20)] for _ in range(20)]
    for i in range(20):
        board[0][i] = '#'
        board[19][i] = '#'
        board[i][0] = '#'
        board[i][19] = '#'
    
    # 10 obstacles
    obstacles = 0
    while obstacles < 10:
        r = random.randint(1, 18)
        c = random.randint(1, 18)
        if board[r][c] == '.':
            board[r][c] = 'O'
            obstacles += 1
            
    # Initial snake (tail to head)
    # let's put snake at 8, 4 (tail), 8, 5 (body), 8, 6 (head)
    # wait, prompt says: length 3, default direction UP.
    # Initial positions random but safe? "随地图输入"
    # let's just put it somewhere safe.
    snake = [(8, 4), (8, 5), (8, 6)]
    board[8][4] = 'B'
    board[8][5] = 'B'
    board[8][6] = 'H'
    
    # Food
    food_r, food_c = 0, 0
    def spawn_food():
        nonlocal food_r, food_c
        empty_cells = [(r, c) for r in range(20) for c in range(20) if board[r][c] == '.']
        if not empty_cells:
            return False
        food_r, food_c = random.choice(empty_cells)
        board[food_r][food_c] = 'F'
        return True
        
    spawn_food()
    
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1
    )
    
    def send(msg):
        proc.stdin.write(msg + '\n')
        proc.stdin.flush()
        
    def read_line():
        return proc.stdout.readline().strip()
        
    # initial output
    for r in range(20):
        send(''.join(board[r]))
    send(str(n))
    
    score = 0
    steps = 0
    last_dir = 'W' # default UP but it's W in WASD
    dir_map = {'W': (-1, 0), 'S': (1, 0), 'A': (0, -1), 'D': (0, 1)}
    
    while True:
        if proc.poll() is not None:
            # Process died early?
            break
            
        move_dir = read_line()
        if not move_dir:
            break
        claimed_score_str = read_line()
        try:
            claimed_score = int(claimed_score_str)
        except ValueError:
            sys.stderr.write(f"Invalid claimed score format: {claimed_score_str}\n")
            break
            
        if claimed_score != score:
            sys.stderr.write(f"Score mismatch at step {steps}. Actual: {score}, Claimed: {claimed_score}\n")
            break
        
        move_dir = move_dir.upper()
        if move_dir not in ['W', 'A', 'S', 'D']:
            sys.stderr.write(f"Invalid move: {move_dir}\n")
            break
            
        r, c = snake[-1]
        dr, dc = dir_map[move_dir]
        nr, nc = r + dr, c + dc
        
        steps += 1
        
        # Check collision
        if board[nr][nc] in ['#', 'O', 'B'] and not (nr == snake[0][0] and nc == snake[0][1]):
            # crash
            send("100 100")
            break
            
        ate_food = (board[nr][nc] == 'F')
        grew_from_n = (steps % n == 0)
        
        snake.append((nr, nc))
        board[r][c] = 'B'
        board[nr][nc] = 'H'
        
        # Determine if tail shrinks
        tail_grows = 0
        if ate_food:
            score += 10
            tail_grows += 1
        if grew_from_n:
            tail_grows += 1
            
        if ate_food and grew_from_n:
            tail_grows = 1
            
        if tail_grows == 0:
            tr, tc = snake.pop(0)
            board[tr][tc] = '.'
        # else tail stays where it is, snake effectively grew
            
        if ate_food:
            if not spawn_food():
                # Game won?
                send("100 100")
                break
            send(f"{food_r} {food_c}")
        else:
            send("20 20")
            
    # Read final output
    final_map = []
    for _ in range(20):
        final_map.append(read_line())
        
    final_score_str = read_line()
    try:
        final_score = int(final_score_str)
        if final_score != score:
            sys.stderr.write(f"Final score mismatch. Actual: {score}, Claimed: {final_score}\n")
            proc.kill()
            sys.exit(1)
    except ValueError:
        sys.stderr.write(f"Invalid final score format: {final_score_str}\n")
        proc.kill()
        sys.exit(1)
        
    # Validation successful
    print(json.dumps({"raw_score": score}))
    
    proc.kill()
    sys.exit(0)

if __name__ == "__main__":
    main()
