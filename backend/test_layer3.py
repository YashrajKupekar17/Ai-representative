"""
Layer 3 test: interactive terminal chat with the agent.
Run: cd backend && source .venv/bin/activate && python test_layer3.py

Type your messages, press Enter. Type 'quit' to exit.
Streams response tokens in real-time.
"""

from app.core.agent import run_agent_streaming


def main():
    print("=" * 60)
    print("AI Persona — Terminal Chat (Layer 3 Test)")
    print("Type 'quit' to exit")
    print("=" * 60)

    messages = []

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break

        messages.append({"role": "user", "content": user_input})

        print("\nAI: ", end="", flush=True)
        full_response = ""
        sources = []

        for chunk_type, data in run_agent_streaming(messages):
            if chunk_type == "token":
                print(data, end="", flush=True)
                full_response += data
            elif chunk_type == "sources":
                sources = data

        print()  # newline after response

        if sources:
            print(f"\n  [Sources: {', '.join(s['tool'] for s in sources)}]")

        messages.append({"role": "assistant", "content": full_response})


if __name__ == "__main__":
    main()
