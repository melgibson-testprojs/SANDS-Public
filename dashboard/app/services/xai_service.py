import os
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
        
        # 1. Start with the latest 80 events for overall system state
        selected_events = all_events[:80]
        
        # 2. If we have a user message, look for relevant historical events (keyword-based)
        if user_message:
            keywords = [k.lower() for k in user_message.split() if len(k) > 3]
            # Add some common security/swarm keywords if they appear in the query
            important_terms = ["vote", "request", "consensus", "attack", "suspicious", "blocked", "agent", "leader"]
            for term in important_terms:
                if term in user_message.lower():
                    keywords.append(term)
            
            keywords = list(set(keywords)) # Unique keywords
            
            if keywords:
                relevant_history = []
                for e in all_events[80:]: # Search beyond the already included recent events
                    desc_lower = e["description"].lower()
                    meta_str = " ".join([str(v).lower() for v in e["metadata"].values()])
                    if any(kw in desc_lower or kw in meta_str for kw in keywords):
                        relevant_history.append(e)
                        if len(relevant_history) >= 40: # Limit historical context to 40 events
                            break
                selected_events.extend(relevant_history)

        # Re-sort combined events by timestamp descending
        selected_events.sort(key=lambda x: x["timestamp"], reverse=True)
        
        context_lines = []
        for e in selected_events[:150]: # Final hard limit
            meta_str = ", ".join([f"{k}={v}" for k, v in e["metadata"].items()])
            line = f"[{e['timestamp']}] {e['severity']} | {e['source']} | {e['category']} | {e['description']} | Meta: {meta_str}"
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
