import os
os.environ["USE_TF"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import sys
from agent import agent_loop

# Fix encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("="*60)
    print("Welcome to the Multi-Tournament Sports Analysis Agent!")
    print("Type 'exit' or 'quit' to stop.")
    print("="*60)

    while True:
        try:
            question = input("\nUser Question: ").strip()
            
            if not question:
                continue
                
            if question.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            result = agent_loop.run_agent(question)

            print("\n" + "="*50)
            print("FINAL ANSWER:")
            print("="*50)
            print(result["answer"])

            print("\n" + "="*50)
            print(f"TRACE (Steps Used: {result['steps_used']}/8):")
            print("="*50)
            for step in result["trace"]:
                print(f"Step {step['step']}: {step['tool']}")
                print(f"Input: {step['input']}")
                output_str = str(step['output'])
                if len(output_str) > 200:
                    output_str = output_str[:200] + "..."
                print(f"Output: {output_str}")
                print("-" * 50)
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
