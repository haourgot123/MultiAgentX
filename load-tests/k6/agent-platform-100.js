import http from 'k6/http'
import { check, sleep } from 'k6'
import { Trend } from 'k6/metrics'

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000'
const API_BASE_URL = `${BASE_URL}/api`
const RUN_STREAMS = (__ENV.RUN_STREAMS || '').toLowerCase() === 'true'
const CHAT_CONVERSATION_ID = __ENV.CHAT_CONVERSATION_ID

export const nonStreamLatency = new Trend('non_stream_latency')
export const streamLatency = new Trend('stream_latency')

export const options = {
  scenarios: {
    agent_platform_100: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 100),
      duration: __ENV.DURATION || '30m',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    non_stream_latency: ['p(95)<500'],
  },
}

function authHeaders(token) {
  return {
    headers: {
      'Content-Type': 'application/json',
      Token: token,
    },
  }
}

export function setup() {
  if (__ENV.TOKEN) {
    return { token: __ENV.TOKEN }
  }

  const username = __ENV.TEST_USERNAME
  const password = __ENV.TEST_PASSWORD
  if (!username || !password) {
    throw new Error('Set TOKEN or TEST_USERNAME/TEST_PASSWORD before running k6')
  }

  const response = http.post(
    `${API_BASE_URL}/authentication/login`,
    JSON.stringify({ username, password }),
    { headers: { 'Content-Type': 'application/json' } },
  )

  check(response, {
    'login succeeded': (res) => res.status === 200 && !!res.json('access_token'),
  })

  return { token: response.json('access_token') }
}

function recordNonStream(response, name) {
  nonStreamLatency.add(response.timings.duration, { name })
  check(response, {
    [`${name} ok`]: (res) => res.status >= 200 && res.status < 400,
  })
}

export default function (data) {
  const params = authHeaders(data.token)

  recordNonStream(http.get(`${API_BASE_URL}/conversations`, params), 'list_conversations')
  recordNonStream(http.get(`${API_BASE_URL}/files`, params), 'list_files')
  recordNonStream(http.get(`${API_BASE_URL}/video-generations`, params), 'list_videos')
  recordNonStream(http.get(`${API_BASE_URL}/skills`, params), 'list_skills')

  if (RUN_STREAMS && CHAT_CONVERSATION_ID) {
    const streamResponse = http.post(
      `${API_BASE_URL}/conversations/chat`,
      JSON.stringify({
        chat_type: 'normal',
        conversation_id: Number(CHAT_CONVERSATION_ID),
        user_question: 'Health check: answer in one short sentence.',
        route_preference: 'auto',
      }),
      params,
    )
    streamLatency.add(streamResponse.timings.duration, { name: 'normal_chat_stream' })
    check(streamResponse, {
      'normal chat stream accepted': (res) => res.status === 201,
      'normal chat stream completed': (res) => res.body && res.body.includes('event: done'),
    })
  }

  sleep(1)
}
