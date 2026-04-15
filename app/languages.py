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
}
