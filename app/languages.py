LANGUAGES = {
    "c": {
        "label": "C (c11)",
        "source_name": "main.c",
        "compile": "gcc /workspace/main.c -O2 -std=c11 -o /workspace/main",
        "run": "/workspace/main",
        "editor_language": "c",
        "default_code": '#include <stdio.h>\n\nint main(void) {\n    long long a, b;\n    if (scanf("%lld %lld", &a, &b) != 2) {\n        return 0;\n    }\n    printf("%lld\\n", a + b);\n    return 0;\n}\n',
    },
    "cpp17": {
        "label": "C++17",
        "source_name": "main.cpp",
        "compile": "g++ /workspace/main.cpp -O2 -std=c++17 -o /workspace/main",
        "run": "/workspace/main",
        "editor_language": "cpp",
        "default_code": "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    long long a, b;\n    cin >> a >> b;\n    cout << a + b << '\\n';\n    return 0;\n}\n",
    },
    "python3": {
        "label": "Python 3",
        "source_name": "main.py",
        "compile": "python3 -m py_compile /workspace/main.py",
        "run": "python3 /workspace/main.py",
        "editor_language": "python",
        "default_code": "import sys\n\ndef main():\n    # Read initial map\n    try:\n        board = [input().strip() for _ in range(20)]\n        n = int(input().strip())\n        score = 0\n        \n        while True:\n            print('W')\n            print(score)\n            sys.stdout.flush()\n            \n            resp = input().strip()\n            if resp == '100 100':\n                for row in board:\n                    print(row)\n                print(score)\n                sys.stdout.flush()\n                break\n            elif len(resp.split()) == 2 and resp != '20 20':\n                score += 10\n    except EOFError:\n        pass\n\nif __name__ == '__main__':\n    main()\n",
    },
}
