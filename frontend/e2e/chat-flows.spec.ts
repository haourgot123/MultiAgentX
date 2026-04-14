import { expect, test, type Page, type Route } from '@playwright/test'

type ConversationSession = {
    id: number
    title: string
    chat_type: 'normal' | 'file'
    file_ids: number[]
    message_count: number
    created_at: string
    updated_at: string
}

type ConversationMessage = {
    id: number
    role: 'user' | 'assistant'
    content: string
    created_at: string
    updated_at: string
}

type FilePayload = {
    id: number
    name: string
    storage_path: string
    mime_type: string
    size: number
    ingestion_status: string
    ingestion_error: string | null
    ingested_chunks: number
    ingested_at: string | null
    created_at: string
    updated_at: string
}

const authStorage = {
    isAuthenticated: true,
    user: {
        id: 1,
        username: 'tester',
        fullName: 'Test User',
        email: 'test@example.com',
        dateOfBirth: '',
        roles: ['user'],
        gender: '',
        country: 'VN',
        phoneNumber: '',
    },
    accessToken: 'playwright-token',
    refreshToken: 'playwright-refresh',
}

const persistValue = (state: unknown) => JSON.stringify({ state, version: 0 })

async function primeAuthenticatedApp(
    page: Page,
    chatState?: { currentChatId: number | null; mode: 'normal' | 'file' | 'deepResearch' | 'webSearch' }
) {
    await page.addInitScript(
        ({ auth, chat }) => {
            window.localStorage.setItem('auth-storage', JSON.stringify({ state: auth, version: 0 }))
            if (chat) {
                window.sessionStorage.setItem('chat-storage', JSON.stringify({ state: chat, version: 0 }))
            } else {
                window.sessionStorage.removeItem('chat-storage')
            }
        },
        { auth: authStorage, chat: chatState ?? null }
    )
}

async function fulfillJson(route: Route, payload: unknown, status = 200) {
    await route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(payload),
    })
}

async function mockChatApi(page: Page, options?: {
    sessions?: ConversationSession[]
    messagesByConversation?: Record<number, ConversationMessage[]>
    files?: FilePayload[]
}) {
    let nextConversationId = 100
    let nextMessageId = 1000
    const sessions = [...(options?.sessions ?? [])]
    const messagesByConversation = structuredClone(options?.messagesByConversation ?? {}) as Record<number, ConversationMessage[]>
    const files = [...(options?.files ?? [])]

    await page.route('**/socket.io/**', async (route) => {
        await route.abort()
    })

    await page.route('**/api/**', async (route) => {
        const request = route.request()
        const url = new URL(request.url())
        const path = url.pathname
        const method = request.method()

        if (path === '/api/meta/phone-countries' && method === 'GET') {
            await fulfillJson(route, [])
            return
        }

        if (path === '/api/files' && method === 'GET') {
            await fulfillJson(route, files)
            return
        }

        const downloadMatch = path.match(/^\/api\/files\/(\d+)\/download$/)
        if (downloadMatch && method === 'GET') {
            const target = files.find((file) => file.id === Number(downloadMatch[1]))
            await route.fulfill({
                status: 200,
                contentType: target?.mime_type || 'text/plain',
                body: 'Playwright file content',
            })
            return
        }

        if (path === '/api/conversations' && method === 'GET') {
            const chatType = url.searchParams.get('chat_type')
            const filtered = chatType ? sessions.filter((session) => session.chat_type === chatType) : sessions
            await fulfillJson(route, filtered)
            return
        }

        if (path === '/api/conversations' && method === 'POST') {
            const body = JSON.parse(request.postData() || '{}')
            const now = new Date().toISOString()
            const session: ConversationSession = {
                id: nextConversationId++,
                title: body.chat_type === 'file' ? 'New file conversation' : 'New conversation',
                chat_type: body.chat_type,
                file_ids: body.file_ids || [],
                message_count: 0,
                created_at: now,
                updated_at: now,
            }
            sessions.unshift(session)
            messagesByConversation[session.id] = []
            await fulfillJson(route, session, 201)
            return
        }

        const detailMatch = path.match(/^\/api\/conversations\/(\d+)$/)
        if (detailMatch && method === 'GET') {
            const conversationId = Number(detailMatch[1])
            const session = sessions.find((item) => item.id === conversationId)
            if (!session) {
                await fulfillJson(route, { detail: 'Not found' }, 404)
                return
            }
            await fulfillJson(route, {
                ...session,
                messages: messagesByConversation[conversationId] || [],
            })
            return
        }

        const addMessageMatch = path.match(/^\/api\/conversations\/(\d+)\/messages$/)
        if (addMessageMatch && method === 'POST') {
            const conversationId = Number(addMessageMatch[1])
            const body = JSON.parse(request.postData() || '{}')
            const now = new Date().toISOString()
            const message: ConversationMessage = {
                id: nextMessageId++,
                role: body.role,
                content: body.content,
                created_at: now,
                updated_at: now,
            }
            messagesByConversation[conversationId] = [...(messagesByConversation[conversationId] || []), message]
            const sessionIndex = sessions.findIndex((item) => item.id === conversationId)
            sessions[sessionIndex] = {
                ...sessions[sessionIndex],
                message_count: messagesByConversation[conversationId].length,
                updated_at: now,
            }
            await fulfillJson(route, {
                message,
                conversation: sessions[sessionIndex],
            }, 201)
            return
        }

        if (path === '/api/conversations/chat' && method === 'POST') {
            const body = JSON.parse(request.postData() || '{}')
            const conversationId = body.conversation_id as number
            const now = new Date().toISOString()
            const assistantContent = body.chat_type === 'file'
                ? 'Grounded answer from file context [1.1]'
                : 'Normal answer from stream.'

            messagesByConversation[conversationId] = [
                ...(messagesByConversation[conversationId] || []),
                {
                    id: nextMessageId++,
                    role: 'user',
                    content: body.user_question,
                    created_at: now,
                    updated_at: now,
                },
                {
                    id: nextMessageId++,
                    role: 'assistant',
                    content: assistantContent,
                    created_at: now,
                    updated_at: now,
                },
            ]

            const sessionIndex = sessions.findIndex((item) => item.id === conversationId)
            sessions[sessionIndex] = {
                ...sessions[sessionIndex],
                message_count: messagesByConversation[conversationId].length,
                updated_at: now,
            }

            const sseBody = [
                'event: status\n',
                'data: {"message":"Thinking"}\n\n',
                'event: token\n',
                `data: ${JSON.stringify({ delta: assistantContent })}\n\n`,
                'event: done\n',
                `data: ${JSON.stringify({ citations: body.chat_type === 'file' ? [{ citation_label: '1.1', file_id: 50, file_name: 'notes.txt', page_no: 1, chunk_index: 0 }] : [] })}\n\n`,
            ].join('')

            await route.fulfill({
                status: 201,
                headers: { 'content-type': 'text/event-stream' },
                body: sseBody,
            })
            return
        }

        if (path === '/api/conversations/deep-research/plan' && method === 'POST') {
            await fulfillJson(route, {
                session_id: 'plan-session-1',
                plan: [
                    'Collect the latest OCR benchmark changes',
                    'Compare PP-OCRv5 against competing pipelines',
                ],
                message: 'Plan created',
            })
            return
        }

        if (path === '/api/conversations/deep-research/approve' && method === 'POST') {
            const body = JSON.parse(request.postData() || '{}')
            const session = sessions.find((item) => item.id === 3)
            const now = new Date().toISOString()
            messagesByConversation[3] = [
                ...(messagesByConversation[3] || []),
                {
                    id: nextMessageId++,
                    role: 'assistant',
                    content: `Deep research final answer based on ${body.approved_plan.length} steps.`,
                    created_at: now,
                    updated_at: now,
                },
            ]

            if (session) {
                session.updated_at = now
                session.message_count = messagesByConversation[3].length
            }

            const sseBody = [
                'event: status\n',
                'data: {"message":"Researching sources"}\n\n',
                'event: token\n',
                `data: ${JSON.stringify({ delta: 'Deep research final answer based on 2 steps.' })}\n\n`,
                'event: done\n',
                'data: {"message":"done"}\n\n',
            ].join('')

            await route.fulfill({
                status: 201,
                headers: { 'content-type': 'text/event-stream' },
                body: sseBody,
            })
            return
        }

        await route.continue()
    })
}

test('streams a normal chat response end-to-end', async ({ page }) => {
    await primeAuthenticatedApp(page)
    await mockChatApi(page)

    await page.goto('/')
    await page.getByPlaceholder('Ask anything...').fill('What is OCR?')
    await page.getByPlaceholder('Ask anything...').press('Enter')

    await expect(page.getByText('What is OCR?')).toBeVisible()
    await expect(page.getByText('Normal answer from stream.')).toBeVisible()
})

test('runs file chat with grounded citations', async ({ page }) => {
    await primeAuthenticatedApp(page, { currentChatId: 2, mode: 'file' })
    await mockChatApi(page, {
        sessions: [
            {
                id: 2,
                title: 'File conversation',
                chat_type: 'file',
                file_ids: [50],
                message_count: 0,
                created_at: '2026-04-15T10:00:00Z',
                updated_at: '2026-04-15T10:00:00Z',
            },
        ],
        messagesByConversation: { 2: [] },
        files: [
            {
                id: 50,
                name: 'notes.txt',
                storage_path: 'tmp/notes.txt',
                mime_type: 'text/plain',
                size: 512,
                ingestion_status: 'completed',
                ingestion_error: null,
                ingested_chunks: 3,
                ingested_at: '2026-04-15T10:05:00Z',
                created_at: '2026-04-15T10:00:00Z',
                updated_at: '2026-04-15T10:05:00Z',
            },
        ],
    })

    await page.goto('/chat-file')
    await expect(page.getByRole('heading', { name: 'notes.txt' })).toBeVisible()
    await page.getByPlaceholder('Ask anything...').fill('Summarize the attached file')
    await page.getByPlaceholder('Ask anything...').press('Enter')

    await expect(page.getByText('Grounded answer from file context')).toBeVisible()
    await expect(page.locator('[data-citation-label="1.1"]')).toBeVisible()
})

test('creates and approves a deep research plan', async ({ page }) => {
    await primeAuthenticatedApp(page, { currentChatId: 3, mode: 'normal' })
    await mockChatApi(page, {
        sessions: [
            {
                id: 3,
                title: 'Deep research chat',
                chat_type: 'normal',
                file_ids: [],
                message_count: 0,
                created_at: '2026-04-15T10:00:00Z',
                updated_at: '2026-04-15T10:00:00Z',
            },
        ],
        messagesByConversation: { 3: [] },
    })

    await page.goto('/')
    const deepResearchToggle = page.getByRole('button', { name: /^Deep Research$/ })
    await deepResearchToggle.click()
    await expect(deepResearchToggle).toHaveAttribute('aria-pressed', 'true')
    await page.getByPlaceholder('Ask anything...').fill('Research the OCR market for me')
    await page.getByPlaceholder('Ask anything...').press('Enter')

    await expect(page.getByText('Collect the latest OCR benchmark changes')).toBeVisible()
    await page.getByRole('button', { name: /accept & start research/i }).click()

    await expect(page.getByText('Deep research final answer based on 2 steps.')).toBeVisible()
})