"use client"

export const CUSTOMER_KEY = "hm_customer_id"
export const BAG_KEY = "hm_bag"

export const DEFAULT_CUSTOMER = "00000dbacae5abe5e23885899a1fa44253a17956c6d1c3d2f588aa139fdfc657"

export function getCustomerId(): string {
  if (typeof window === "undefined") return DEFAULT_CUSTOMER
  try {
    return localStorage.getItem(CUSTOMER_KEY) || DEFAULT_CUSTOMER
  } catch {
    return DEFAULT_CUSTOMER
  }
}

export function setCustomerId(id: string) {
  localStorage.setItem(CUSTOMER_KEY, id.trim())
}

export function setCustomerIdStored(id: string) {
  setCustomerId(id)
}


export function loginNewCustomer(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  const id = Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
  setCustomerId(id)
  return id
}

export function logoutCustomer() {
  localStorage.removeItem(CUSTOMER_KEY)
  localStorage.removeItem(BAG_KEY)
  localStorage.removeItem(LOGIN_KEY)
}

const LOGIN_KEY = "hm_login_id"

export function getLoginId(): string {
  if (typeof window === "undefined") return ""
  try {
    return localStorage.getItem(LOGIN_KEY) || ""
  } catch {
    return ""
  }
}

export function setLoginId(id: string) {
  localStorage.setItem(LOGIN_KEY, id.trim().toLowerCase())
}
