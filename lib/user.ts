const USER_ID_KEY = "study-ai-user-id";

export function getUserId(): string {
  const existingId = window.localStorage.getItem(USER_ID_KEY);

  if (existingId) {
    return existingId;
  }

  const newId = crypto.randomUUID();
  window.localStorage.setItem(USER_ID_KEY, newId);

  return newId;
}
