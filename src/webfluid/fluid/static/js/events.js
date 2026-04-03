import { createWS } from "./base.js"

const { request } = createWS("/ws/events")


export class EventManager {
    constructor() {
        this._events = {}
        this._break_flag = {}
        this._event_loops = {}
    }

    async _event_loop(event){
        if (!this._events[event]) return

        let listener = request("listen", event)

        while (!this._break_flag[event]) {
            const response = await listener
            if (!response?.data) {
                console.error("Error while listening: " + response.error)
                break
            } else if (this._break_flag[event]) break
            listener = request("listen", event)

            for (const handler of this._events[event]) {
                handler(response.data)
            }
        }
    }

    registerHandler(event, handler) {
        if (!this._events[event]) throw new Error("Event not subscribed: " + event)
        this._events[event].push(handler)
    }

    async subscribe(event) {
        if (this._events[event]) throw new Error("Event already subscribed: " + event)

        const response = await request("subscribe",  event)
        if (!response?.data) throw new Error(response.error)

        this._events[event] = []
        this._break_flag[event] = false
        this._event_loops[event] = this._event_loop(event)
    }

    async unsubscribe(event) {
        if (!this._events[event]) throw new Error("Event not subscribed: " + event)

        const response = await request("unsubscribe",  event)
        if (!response?.data) throw new Error(response.error)

        delete this._events[event]
        this._break_flag[event] = true
        await this._event_loops[event]
        delete this._event_loops[event]
    }
}


window.wf.ext.events = { EventManager, eventRequest: request }
