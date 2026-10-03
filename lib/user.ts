const FIXED_USER_ID = "da01e100-0001-0000-0000-000000000001";

export function getUserId(): string {
  if (typeof window === "undefined") {
    return FIXED_USER_ID;
  }

  let id = localStorage.getItem("study-ai-user-id");
  if (!id) {
    id = FIXED_USER_ID;
    localStorage.setItem("study-ai-user-id", id);
  }
  return id;
}
