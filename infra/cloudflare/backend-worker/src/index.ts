import { Container, getContainer } from '@cloudflare/containers'

export class DroneOptAPI extends Container {
  defaultPort = 8000
  sleepAfter = '10m'
  enableInternet = true
  envVars = {
    CORS_ORIGINS: 'https://droneoptai.bvphuc28.workers.dev',
    DATABASE_URL: 'sqlite:///./droneoptai.db'
  }
}

export default {
  async fetch(request: Request, env: { DRONEOPT_API: DurableObjectNamespace }): Promise<Response> {
    return getContainer(env.DRONEOPT_API, 'api').fetch(request)
  },
}
