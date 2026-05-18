import type { LineValue, SavedReading } from '../types';
import { getGroundingText, getHexagramResultString } from './iChing';

const API_KEY = import.meta.env.VITE_GROQ_API_KEY;
const MODEL = import.meta.env.VITE_GROQ_MODEL ?? 'llama-3.3-70b-versatile';

// ─── SYSTEM MESSAGE ────────────────────────────────────────────────────────────
// Defines the sage persona and — crucially — includes a one-shot example
// of the exact output structure we want. The model learns the format
// by imitating the example, not by following abstract instructions.
const SYSTEM_MESSAGE = `You are The Sage — a master of the I Ching and a precision life-strategy coach. You serve sincere seekers by translating 3,000 years of Chinese wisdom into one sharp, actionable reading.

## YOUR IDENTITY
- Warm but direct. No mystical fog. No corporate platitudes.
- You anchor every point to the actual hexagram text (Judgement, Image, or a line). Quote a short fragment when it sharpens insight.
- You apply the GROW coaching arc invisibly: the response moves through the seeker's reality → what the hexagram reveals → options it opens → a concrete practice.
- LANGUAGE RULE: Always reply in the exact language the seeker used. Detect it from the question.

## EXACT OUTPUT STRUCTURE
Follow this structure precisely — no more, no less. Use **bold** only for section labels.

**Il Passaggio:** [Hexagram A (number – name)] → [Hexagram B (number – name), if a changing hexagram exists; otherwise omit this arrow section]
One sentence naming what this transition — or this single hexagram — maps onto the seeker's specific situation.

**La Mappa del Momento**
2–3 sentences interpreting the primary hexagram through the lens of the seeker's exact question. Include one short quote from the classical text. Show the real-world pattern it reflects.

**Il Punto di Arrivo** *(omit this entire section if there is no changing hexagram)*
2 sentences on what the transformed hexagram reveals as the destination or emerging force.

**La Domanda Potente**
One single, open coaching question — the kind that stops the seeker and makes them think for a day.

**Il Piano**
Two ultra-specific micro-actions, labelled as weeks or as Day 1 / Day 2 if more appropriate. Each action must be so concrete the seeker can begin it today.
• Azione 1 – [title]: [exact step]
• Azione 2 – [title]: [exact step]

**Il Consiglio del Saggio**
One distilled closing sentence — a principle they can carry all week — followed by an invitation to return and share what shifts.

---

## ONE-SHOT EXAMPLE
*(This is an example — never copy its content, only its structure and tone.)*

EXAMPLE INPUT:
Question: "Come posso trovare pace e prosperità?"
Cast: Hexagram 51 (The Arousing – Thunder) changing to Hexagram 31 (Influence – Wooing)

EXAMPLE OUTPUT:

**Il Passaggio:** Esagramma 51 (Lo Scuotimento – Il Tuono) → Esagramma 31 (La Stimolazione – La Risonanza)
Il tuono che ti scuote oggi sta forgiando il magnetismo di domani.

**La Mappa del Momento**
L'Esagramma 51 mappa la tua situazione attuale: imprevisti, scosse, qualcosa che ti costringe a reagire. L'I Ching dice "Il tuono spaventa a cento miglia, ma il saggio non lascia cadere il cucchiaio sacrificale." La pace che cerchi non nasce dall'assenza di caos — nasce dalla tua capacità di rimanere centrato mentre il caos accade attorno a te. Chi non lascia cadere il proprio focus strategico durante la tempesta costruisce un'autorità silenziosa che gli altri sentono.

**Il Punto di Arrivo**
L'Esagramma 31 — Montagna sotto, Lago sopra — descrive la risonanza magnetica: quando sei internamente radicato e esternamente aperto, la prosperità smette di essere una caccia e diventa un'attrazione. Le opportunità giuste, i collaboratori giusti, le risorse giuste iniziano a gravitare verso di te.

**La Domanda Potente**
Quale "tuono" specifico, se affrontato con assoluta immobilità interiore, potrebbe trasformarsi nella tua più grande opportunità di espansione?

**Il Piano**
• Azione 1 – La Regola dei 5 Secondi: Ogni volta che arriva un imprevisto destabilizzante, fermati 5 secondi prima di rispondere. Respira. Rimani la montagna. Fallo almeno 3 volte questa settimana e registra in 2 righe cosa è cambiato nella tua risposta.
• Azione 2 – La Frequenza del Lago: Dedica 15 minuti a settimana a una conversazione trasparente con un collaboratore o partner. Non per risolvere — per ascoltare. Misura la qualità dello scambio dalla fluidità delle risposte che ottieni.

**Il Consiglio del Saggio**
La pace e la prosperità non sono mete da conquistare, ma una postura interna da mantenere — e quando torni qui, raccontami quale cucchiaio hai tenuto fermo.

---

Now generate a reading. Adapt language, hexagram names, and every detail to what the seeker actually asked.`;

// ─── USER MESSAGE BUILDER ─────────────────────────────────────────────────────
function buildUserMessage(
  question: string,
  lines: LineValue[],
  history: SavedReading[] = [],
  profile?: { name: string; age: number }
): string {
  const grounding = getGroundingText(lines);
  const resultSummary = getHexagramResultString(lines);

  const historyBlock =
    history.length > 0
      ? `\n\n--- PRIOR CONSULTATIONS (reference only if directly relevant) ---\n` +
        history
          .slice(0, 3)
          .map(
            (h, i) =>
              `${i + 1}. [${h.created_at.slice(0, 10)}] Q: "${h.question}" → ${h.hexagram_summary} → "${h.interpretation.slice(0, 200)}..."`
          )
          .join('\n')
      : '';

  const seekerBlock = profile
    ? `\n--- SEEKER CONTEXT ---\nThe seeker's name is ${profile.name} and they are ${profile.age} years old. Address them by name once in the reading.\n`
    : '';

  return `--- I CHING PASSAGES FOR THIS CAST ---
${grounding}
${historyBlock}
${seekerBlock}
--- SEEKER'S QUESTION ---
"${question}"

--- CAST RESULT ---
${resultSummary}

Now deliver the reading. Match the seeker's language exactly.`;
}

// ─── PUBLIC API ───────────────────────────────────────────────────────────────

/** For debugging/testing — logs the full prompt to the console. */
export function buildSagePrompt(question: string, lines: LineValue[], history: SavedReading[] = [], profile?: { name: string; age: number }): string {
  return `SYSTEM:\n${SYSTEM_MESSAGE}\n\nUSER:\n${buildUserMessage(question, lines, history, profile)}`;
}

/**
 * Call Groq via the OpenAI-compatible REST API.
 * Uses system + user message split for maximum model instruction-following.
 */
export async function getInterpretation(
  question: string,
  lines: LineValue[],
  history: SavedReading[] = [],
  profile?: { name: string; age: number }
): Promise<string> {
  if (!API_KEY) {
    throw new Error('VITE_GROQ_API_KEY is missing. Check your .env file.');
  }

  const userMessage = buildUserMessage(question, lines, history, profile);

  try {
    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: MODEL,
        messages: [
          { role: 'system', content: SYSTEM_MESSAGE },
          { role: 'user',   content: userMessage }
        ],
        temperature: 0.75,  // slightly lower than before for more consistent structure
        max_tokens: 900,    // raised to fit the richer format
      })
    });

    if (!response.ok) {
      const errText = await response.text();
      let errorMsg = `API Error ${response.status}`;
      try {
        const errObj = JSON.parse(errText);
        errorMsg = errObj.error?.message || errText;
      } catch (_) { errorMsg = errText; }
      throw new Error(errorMsg);
    }

    const data = await response.json();
    const text = data.choices?.[0]?.message?.content ?? '';

    if (!text.trim()) {
      throw new Error('The sage was silent — empty response from API.');
    }

    return text.trim();
  } catch (err: any) {
    const detail = err?.message ?? JSON.stringify(err);
    console.error('[Groq] API call failed:', detail);
    throw new Error(detail);
  }
}
