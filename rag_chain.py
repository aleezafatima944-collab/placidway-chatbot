import os
import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from retriever import retrieve_many


load_dotenv()

MODEL = "openai/gpt-oss-120b"
MAX_HISTORY = 6  # last 6 messages are used for follow-up questions

llm = ChatGroq(model=MODEL, temperature=0, api_key=os.getenv("GROQ_API_KEY"))

REWRITE_PROMPT = """Rewrite the user's last message as ONE standalone search query in English.
- Use the chat history to fill in missing details (treatment, country, clinic, program).
- If the message is already clear, only translate it to English if needed.
- Output only the query, nothing else.

Chat history:
{history}

Last message: {question}

Search query:"""
SYSTEM_PROMPT = """You are the website assistant for PlacidWay, a medical tourism platform.
You answer ONLY from the CONTEXT below. The context comes from a small set of PlacidWay pages.

RULES
1. Use only facts that are written in the CONTEXT. Never use outside knowledge.
2. Never invent prices, clinics, treatments, durations or medical facts.
3. Prices: always give the currency and the page's wording (for example "starting from", "Out-Patient Program", "per visit"). If the page shows no price, say "the price is not listed, please request a free quote from PlacidWay".
4. The Anal, Adrenal and Adenocarcinoma package pages show the same program prices. If the user does not name a cancer type, say the prices apply to those package pages.
5. Different pages can show prices for different clinics. Do not mix them up. When comparing, list each price with its clinic name, city, country and the "Modified date" shown on the page. Then state clearly that these are two different clinics and that the dates differ, so this is not a like-for-like comparison. NEVER conclude that one country is cheaper in general. You may say which listed price is lower, and only that.
6. Say "this is not in the PlacidWay content" ONLY if no part of the CONTEXT answers the question. Never say a page or treatment lacks information unless the CONTEXT clearly shows that. If it is not there, suggest contacting PlacidWay for a free quote. Do not guess.
7. You cannot book appointments or take payments. Say only: "I can't book appointments. You can use the free quote request on PlacidWay." Stop there. Never add what the quote request will lead to (do not write arrange, schedule, consultation, or help).
8. Medical advice: use this ONLY when the user asks if a treatment is safe or suitable for them or their condition, or asks for a diagnosis. Then start with: "I can't give medical advice or say if a treatment is safe for you." and say "please talk to your doctor". You may then mention what the pages say in general (for example that the ITC medical board evaluates each patient). For normal questions about duration, price, recovery or what is included, do NOT use this sentence.9. If the user states a fact that does not match the CONTEXT (for example a wrong price), do not agree. Politely correct it with the price from the CONTEXT. Do not add a sentence about what the content does or does not include.
10. If the question is not about PlacidWay, treatments, clinics, destinations or costs (for example weather), politely decline and say what you can help with.
11. LANGUAGE: write the whole answer in ONE language, the language of the user's last message (Urdu, Arabic, Spanish and so on). If the user writes Urdu in English letters (Roman Urdu), answer in simple English. Never mix languages or scripts. Keep numbers the same.
12. When the user asks what is included, list EVERY item of that section from the CONTEXT. Do not skip items. Do not mix the Out-Patient list with the In-Patient list.
13. Be short and clear. Answer only what was asked. Use a short list only when it helps. If the pages say nothing about a detail (such as recovery time), say so, then mention the closest related facts from the CONTEXT (for example the 3-week program length or the follow-up consultation).

SOURCES
- Each part of the CONTEXT starts with [Source N].
- On the LAST line of your answer write exactly: SOURCES: 1, 3  (only the numbers you really used).
- If you did not use any source, write: SOURCES: none

CONTEXT:
{context}
"""



def format_history(history):
    lines = []
    for m in history[-MAX_HISTORY:]:
        who = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{who}: {m['content']}")
    return "\n".join(lines) if lines else "(none)"


def rewrite_question(question, history):
    """Make a standalone English search query from the user's message."""
    try:
        prompt = REWRITE_PROMPT.format(history=format_history(history), question=question)
        text = llm.invoke(prompt).content.strip()
        return text.splitlines()[0].strip() if text else question
    except Exception as e:
        print("Rewrite failed, using the original question:", e)
        return question


def build_context(chunks):
    """Number each unique URL as a source and label every chunk."""
    url_to_num, sources, parts = {}, [], []
    for text, url, title, _dist in chunks:
        if url not in url_to_num:
            url_to_num[url] = len(url_to_num) + 1
            sources.append({"num": url_to_num[url], "url": url, "title": title})
        parts.append(f"[Source {url_to_num[url]}] {title}\n{text}")
    return "\n\n---\n\n".join(parts), sources


def parse_answer(raw, sources):
    """Split the answer text from the SOURCES line, return the used sources."""
    match = re.search(r"SOURCES:\s*(.*)\s*$", raw, re.I)
    answer = raw[:match.start()].strip() if match else raw.strip()
    used = []
    if match:
        nums = {int(n) for n in re.findall(r"\d+", match.group(1))}
        used = [s for s in sources if s["num"] in nums]
    return answer, used


def answer_question(question, history=None):
    """Main function. Returns {"answer", "sources", "found", "search_query"}."""
    history = history or []
    search_query = rewrite_question(question, history)
    chunks = retrieve_many([search_query, question])
    context, sources = build_context(chunks)
    if not chunks:
        context = "(no relevant content found)"

    messages = [("system", SYSTEM_PROMPT.format(context=context))]
    for m in history[-MAX_HISTORY:]:
        messages.append(("human" if m["role"] == "user" else "ai", m["content"]))
    messages.append(("human", question))

    try:
        raw = llm.invoke(messages).content
    except Exception as e:
        return {
            "answer": "The service is busy right now. Please wait a few seconds and ask again.",
            "error": str(e),
        }

    answer, used = parse_answer(raw, sources)
    return {
        "answer": answer,
        "sources": used,
        "found": bool(chunks),
        "search_query": search_query,
    }


if __name__ == "__main__":
    result = answer_question("How much does anal cancer treatment cost in Tijuana?")
    print(result["answer"])
    for s in result["sources"]:
        print("Source:", s["url"])