import os
import re
from typing import List, Dict, Any
from groq import Groq
from dashboard.app.services.log_aggregator import log_aggregator

class XAIService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
        
        self.system_prompt = (
            "You are SANDS AI, a specialized security analyst assistant for the SANDS SOC (Swarm-based Anomaly Network Detection System). "
            "Your goal is to help users analyze system logs, understand swarm voting activity, and identify security threats. "
            "You have access to the latest system logs which are provided in the context. "
            "Be concise, technical, and professional. If you don't know something, say so. "
            "Always refer to 'LID' as Logical ID and 'Agent ID' as Physical Agent ID."
        )

    def _prepare_context(self, user_message: str = "") -> str:
        all_events = log_aggregator.get_all_events()
        if not all_events:
            return "No system logs available."
        
        # 1. Start with the absolute latest 10 events for immediate pulse
        selected_events = all_events[:10]
        
        # 2. Extract keywords for targeted search
        # Look for: LIDs (hex), Agent IDs (agent-XXX), and typical security terms
        keywords = set()
        
        # Extract hex LIDs (e.g., c21f885fb8fd9700)
        lids = re.findall(r'[a-f0-9]{16}', user_message.lower())
        keywords.update(lids)
        
        # Extract Agent IDs (e.g., agent-local-001)
        agents = re.findall(r'agent-[\w-]+', user_message.lower())
        keywords.update(agents)
        
        # General technical keywords (length > 3)
        words = [k.lower() for k in user_message.split() if len(k) > 3]
        important_terms = {"vote", "consensus", "attack", "suspicious", "blocked", "leader", "risk", "anomaly"}
        for word in words:
            if word in important_terms or word.isalnum():
                keywords.add(word)
        
        # 3. Search for relevant history in the last 1000 events
        if keywords:
            relevant_history = []
            # Skip the 10 we already took
            for e in all_events[10:1000]: 
                desc_lower = e["description"].lower()
                meta_str = " ".join([str(v).lower() for v in e["metadata"].values()]).lower()
                
                if any(kw in desc_lower or kw in meta_str for kw in keywords):
                    relevant_history.append(e)
                    if len(relevant_history) >= 30: # Max 30 relevant historical logs
                        break
            selected_events.extend(relevant_history)

        # 4. Sort by timestamp descending and apply hard cap
        selected_events.sort(key=lambda x: x["timestamp"], reverse=True)
        final_selection = selected_events[:40] # Total hard limit 40
        
        context_lines = []
        for e in final_selection:
            # Token-efficient format: [TS] SRC | CAT | MSG | {META}
            # Trim timestamp to time only if possible, or keep as is for clarity
            ts = e['timestamp'].split(' ')[1] if ' ' in e['timestamp'] else e['timestamp']
            meta = " ".join([f"{k}:{v}" for k, v in e["metadata"].items() if k not in ["component"]])
            line = f"[{ts}] {e['source'].upper()} | {e['category']} | {e['description']} | {meta}".strip()
            context_lines.append(line)
        
        return "\n".join(context_lines)

    async def get_response(self, user_message: str, history: List[Dict[str, str]] = None) -> str:
        if not self.client:
            return "Error: GROQ_API_KEY is not configured. Please set the environment variable and restart the server."

        try:
            context = self._prepare_context(user_message)
            messages = [
                {"role": "system", "content": f"{self.system_prompt}\n\nLATEST & RELEVANT LOG CONTEXT:\n{context}"}
            ]
            
            if history:
                messages.extend(history)
            
            messages.append({"role": "user", "content": user_message})

            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                max_tokens=1024,
            )

            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error communicating with Groq: {str(e)}"

xai_service = XAIService()
