// Same limit as AnalystMessage.message in app/schemas/chat.py.
export const maxMessageLength = 4000

export const chatKey = (caseId: string) => ['chat', caseId] as const
