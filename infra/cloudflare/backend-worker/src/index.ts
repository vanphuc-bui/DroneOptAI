import { Container, getContainer } from '@cloudflare/containers'

export class DroneOptAPI extends Container {
  defaultPort = 8000
  sleepAfter = '10m'
  enableInternet = true
}

export default {
  async fetch(request: Request, env: { DRONEOPT_API: DurableObjectNamespace }): Promise<Response> {
    return getContainer(env.DRONEOPT_API, 'api').fetch(request)
  },
}
