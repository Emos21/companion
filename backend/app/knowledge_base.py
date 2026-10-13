"""Companion's knowledge base: the routine, well-covered questions the bot may
answer on its own. Deliberately generic wellbeing-program content (not tied to any
real organisation). Anything outside this - clinical, crisis, or novel - should
fall through to a human via the escalation engine.
"""

KB: list[dict] = [
    {
        "id": "what-is",
        "title": "What the program is",
        "text": "Companion supports a peer-facilitated group wellbeing program. Small groups meet weekly with a trained peer facilitator to practice evidence-based skills. It is skills practice and peer support, not therapy or medical care.",
    },
    {
        "id": "reschedule",
        "title": "Rescheduling a session",
        "text": "To reschedule, open your dashboard, choose the session, and pick another slot at least 24 hours in advance. Within 24 hours, message your facilitator and they will try to fit you into another group that week.",
    },
    {
        "id": "missed",
        "title": "Missing a session",
        "text": "If you miss a session, you can catch up with the shared session notes in your dashboard and join the next one. Missing a single session does not remove you from your group.",
    },
    {
        "id": "deposit",
        "title": "Deposits and refunds",
        "text": "Some groups ask for a small refundable deposit to hold your place. You get the deposit back automatically once you attend the agreed number of sessions. If you withdraw before the program starts, the deposit is refunded in full within five business days.",
    },
    {
        "id": "cost",
        "title": "Cost",
        "text": "Core group sessions are offered at low or no cost depending on your region and funding. Any fees are shown clearly before you join, and no payment details are needed to browse or apply.",
    },
    {
        "id": "matching",
        "title": "How groups are matched",
        "text": "When you join, you answer a short intake about your goals, language, and availability. Companion uses that to match you to a group that fits your schedule and preferred language.",
    },
    {
        "id": "facilitator",
        "title": "Who facilitators are",
        "text": "Facilitators are trained peers, not clinicians. They guide the group through the session plan, keep the space safe and respectful, and know when to refer something to a staff member or professional.",
    },
    {
        "id": "privacy",
        "title": "Privacy and your data",
        "text": "What you share in a group stays in the group. Your account data is stored securely, used only to run the program, and you can request a copy or deletion at any time from your dashboard settings.",
    },
    {
        "id": "tech",
        "title": "Joining online sessions",
        "text": "Sessions run in your browser. You need a stable internet connection and a device with a microphone. If your video or audio fails, refresh the session link; if it still fails, message your facilitator for a dial-in option.",
    },
    {
        "id": "language",
        "title": "Languages",
        "text": "Groups run in several languages. You can set your preferred language during intake, and Companion will only match you to groups offered in a language you selected.",
    },
    {
        "id": "eligibility",
        "title": "Who can join",
        "text": "The program is open to adults who want structured peer support for everyday wellbeing. It is not a substitute for crisis care or treatment of a diagnosed condition.",
    },
    {
        "id": "leave",
        "title": "Leaving the program",
        "text": "You can leave at any time from your dashboard. There is no penalty, and any refundable deposit is returned per the deposit policy.",
    },
]
