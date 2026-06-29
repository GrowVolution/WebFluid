
function getSystemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
}

function getCurrentTheme() {
    return localStorage.getItem("theme") ?? getSystemTheme()
}

export function updateTheme() {
    document.documentElement.dataset.theme = getCurrentTheme()
}

export function switchTheme() {
    const current = getCurrentTheme()
    const newTheme = current === "light" ? "dark" : "light"

    localStorage.setItem("theme", newTheme)
    updateTheme()
}

export function createWS(path, options = {}) {
    const protocol = location.protocol === "https:" ? "wss" : "ws"

    let ws
    let requestId = 0

    const pending = new Map()
    const queue = []

    let retries = 0
    let reconnecting = false

    const {
        reconnect = true,
        maxDelay = 10000,
        baseDelay = 500,
        timeout = 15000
    } = options

    function connect() {
        ws = new WebSocket(`${protocol}://${location.host}${path}`)

        ws.onopen = () => {
            retries = 0

            const q = queue.splice(0)
            for (const item of q) {
                sendRequest(item.type, item.data)
                    .then(item.resolve)
                    .catch(item.reject)
            }
        }

        ws.onmessage = (event) => {
            let msg
            try {
                msg = JSON.parse(event.data)
            } catch {
                return
            }

            if (msg.id && pending.has(msg.id)) {
                const { resolve, reject } = pending.get(msg.id)
                pending.delete(msg.id)
                if (msg?.error) reject(msg.error)
                else resolve(msg.data)
            }
        }

        ws.onclose = () => {
            for (const [, { reject }] of pending) {
                reject("socket closed")
            }
            pending.clear()

            if (!reconnect || reconnecting) return
            reconnecting = true

            const delay = Math.min(baseDelay * 2 ** retries, maxDelay)
            retries++

            setTimeout(() => {
                reconnecting = false
                connect()
            }, delay)
        }
    }

    function sendRequest(type, data) {
        return new Promise((resolve, reject) => {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                queue.push({ type, data, resolve, reject })
                return
            }

            const id = ++requestId

            const payload = {
                id,
                type,
                data
            }

            let timer = null

            if (timeout) {
                timer = setTimeout(() => {
                    if (pending.has(id)) {
                        pending.delete(id)
                        reject("timeout")
                    }
                }, timeout)
            }

            pending.set(id, {
                resolve: (data) => {
                    if (timer) clearTimeout(timer)
                    resolve(data)
                },
                reject: (err) => {
                    if (timer) clearTimeout(timer)
                    reject(err)
                }
            })

            try {
                ws.send(JSON.stringify(payload))
            } catch (err) {
                pending.delete(id)
                reject(err)
            }
        })
    }

    connect()

    return {
        get socket() {
            return ws
        },
        request: sendRequest
    }
}


window.wf = {
    updateTheme,
    switchTheme,
    createWS,

    ext: {},
    adt: {}
}

updateTheme()
