/**
 * Frappe realtime (socket.io), used to stream assistant turns.
 *
 * Mirrors Frappe's own client: same origin in production (nginx proxies
 * /socket.io), `host:socketio_port` in developer mode, namespace = site.
 * If the socket cannot connect the assistant still works: the HTTP reply
 * carries the full answer, only the word-by-word streaming is lost.
 */
import { io, type Socket } from 'socket.io-client'

type BootWindow = Window & { site_name?: string; socketio_port?: number | string; dev_server?: boolean }

let socket: Socket | null = null

export function realtimeUrl(win: BootWindow = window as BootWindow): string | null {
  if (!win.site_name) return null
  let host = win.location.origin
  if (win.dev_server) {
    const parts = host.split(':')
    host = `${parts[0]}:${parts[1]}:${win.socketio_port || 9000}`
  }
  return `${host}/${win.site_name}`
}

export function getSocket(): Socket | null {
  if (socket) return socket
  const url = typeof window === 'undefined' ? null : realtimeUrl()
  if (!url) return null
  socket = io(url, { withCredentials: true, reconnectionAttempts: 5, transports: ['websocket', 'polling'] })
  return socket
}

export function onRealtime<T>(event: string, handler: (payload: T) => void): () => void {
  const client = getSocket()
  if (!client) return () => {}
  client.on(event, handler)
  return () => client.off(event, handler)
}
