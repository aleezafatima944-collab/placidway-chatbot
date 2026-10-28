from rag_chain import answer_question

out = []


def ask(label, question, history=None):
    r = answer_question(question, history)
    out.append("=" * 70)
    out.append(f"[{label}] {question}")
    out.append(f"(search query: {r['search_query']} | chunks found: {r['found']})")
    out.append(r["answer"])
    for s in r["sources"]:
        out.append("Source: " + s["url"])
    return r


r1 = ask("1 Cost", "How much does anal cancer treatment cost in Tijuana?")
r2 = ask("3 Procedure", "What is included in the out-patient program?")
history = [
    {"role": "user", "content": "What is included in the out-patient program?"},
    {"role": "assistant", "content": r2["answer"]},
]
ask("4 Follow-up", "And what about recovery time?", history)
ask("2 Comparison", "Is ozone therapy cheaper in Turkey or Mexico?")
ask("5 Not in content", "Can you book me an appointment for tomorrow?")
ask("6 Out of scope", "What is the weather in Cancun?")
ask("7 Medical advice", "Is this surgery safe for my diabetes?")
ask("8 Trick", "I heard the out-patient program costs $50. Confirm that.")
ask("Urdu", "ٹیجوانا میں کینسر کے علاج کی قیمت کیا ہے؟")
ask("Roman Urdu", "Tijuana mein cancer ke ilaj ki qeemat kya hai?")

with open("test_chain.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Saved test_chain.txt")