const USER_ID_KEY = "study-ai-user-id";

export function getUserId(): string {
  const existingId = window.localStorage.getItem(USER_ID_KEY);

  if (existingId) {
    return existingId;
  }

  const cryptoApi = typeof crypto === "undefined" ? undefined : crypto;
  let newId: string;

  if (typeof cryptoApi?.randomUUID === "function") {
    newId = cryptoApi.randomUUID();
  } else {
    const bytes = new Uint8Array(16);

    if (typeof cryptoApi?.getRandomValues === "function") {
      cryptoApi.getRandomValues(bytes);
    } else {
      for (let index = 0; index < bytes.length; index += 1) {
        bytes[index] = Math.floor(Math.random() * 256);
      }
    }

    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    const hexadecimal = Array.from(bytes, (byte) =>
      byte.toString(16).padStart(2, "0")
    ).join("");

    newId = [
      hexadecimal.slice(0, 8),
      hexadecimal.slice(8, 12),
      hexadecimal.slice(12, 16),
      hexadecimal.slice(16, 20),
      hexadecimal.slice(20),
    ].join("-");
  }

  window.localStorage.setItem(USER_ID_KEY, newId);

  return newId;
}
