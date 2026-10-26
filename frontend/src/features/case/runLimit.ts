// The backend stops a run at 300 s and answers 504. The page waits a little longer so that the
// backend's own answer arrives first, and gives up on its own only if the answer never comes.
export const backendLimitSeconds = 300
export const pageLimitMs = (backendLimitSeconds + 20) * 1000

export class RunTimeout extends Error {
  constructor() {
    super('No answer from the backend within the time limit')
    this.name = 'RunTimeout'
  }
}

export function withTimeLimit<T>(request: Promise<T>, ms = pageLimitMs): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined
  const limit = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new RunTimeout()), ms)
  })
  return Promise.race([request, limit]).finally(() => clearTimeout(timer))
}

export function formatElapsed(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`
}
