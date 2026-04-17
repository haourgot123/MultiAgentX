"use strict";
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
Object.defineProperty(exports, "__esModule", { value: true });
var test_1 = require("@playwright/test");
var authStorage = {
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
};
var persistValue = function (state) { return JSON.stringify({ state: state, version: 0 }); };
function primeAuthenticatedApp(page, chatState) {
    return __awaiter(this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, page.addInitScript(function (_a) {
                        var auth = _a.auth, chat = _a.chat;
                        window.localStorage.setItem('auth-storage', JSON.stringify({ state: auth, version: 0 }));
                        if (chat) {
                            window.sessionStorage.setItem('chat-storage', JSON.stringify({ state: chat, version: 0 }));
                        }
                        else {
                            window.sessionStorage.removeItem('chat-storage');
                        }
                    }, { auth: authStorage, chat: chatState !== null && chatState !== void 0 ? chatState : null })];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    });
}
function fulfillJson(route_1, payload_1) {
    return __awaiter(this, arguments, void 0, function (route, payload, status) {
        if (status === void 0) { status = 200; }
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, route.fulfill({
                        status: status,
                        contentType: 'application/json',
                        body: JSON.stringify(payload),
                    })];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    });
}
function mockChatApi(page, options) {
    return __awaiter(this, void 0, void 0, function () {
        var nextConversationId, nextMessageId, sessions, messagesByConversation, files;
        var _this = this;
        var _a, _b, _c;
        return __generator(this, function (_d) {
            switch (_d.label) {
                case 0:
                    nextConversationId = 100;
                    nextMessageId = 1000;
                    sessions = __spreadArray([], ((_a = options === null || options === void 0 ? void 0 : options.sessions) !== null && _a !== void 0 ? _a : []), true);
                    messagesByConversation = structuredClone((_b = options === null || options === void 0 ? void 0 : options.messagesByConversation) !== null && _b !== void 0 ? _b : {});
                    files = __spreadArray([], ((_c = options === null || options === void 0 ? void 0 : options.files) !== null && _c !== void 0 ? _c : []), true);
                    return [4 /*yield*/, page.route('**/socket.io/**', function (route) { return __awaiter(_this, void 0, void 0, function () {
                            return __generator(this, function (_a) {
                                switch (_a.label) {
                                    case 0: return [4 /*yield*/, route.abort()];
                                    case 1:
                                        _a.sent();
                                        return [2 /*return*/];
                                }
                            });
                        }); })];
                case 1:
                    _d.sent();
                    return [4 /*yield*/, page.route('**/api/**', function (route) { return __awaiter(_this, void 0, void 0, function () {
                            var request, url, path, method, downloadMatch, target, chatType_1, filtered, body, now, session, detailMatch, conversationId_1, session, addMessageMatch, conversationId_2, body, now, message, sessionIndex, body, conversationId_3, now, assistantContent, sessionIndex, sseBody, body, session, now, sseBody;
                            return __generator(this, function (_a) {
                                switch (_a.label) {
                                    case 0:
                                        request = route.request();
                                        url = new URL(request.url());
                                        path = url.pathname;
                                        method = request.method();
                                        if (!(path === '/api/meta/phone-countries' && method === 'GET')) return [3 /*break*/, 2];
                                        return [4 /*yield*/, fulfillJson(route, [])];
                                    case 1:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 2:
                                        if (!(path === '/api/files' && method === 'GET')) return [3 /*break*/, 4];
                                        return [4 /*yield*/, fulfillJson(route, files)];
                                    case 3:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 4:
                                        downloadMatch = path.match(/^\/api\/files\/(\d+)\/download$/);
                                        if (!(downloadMatch && method === 'GET')) return [3 /*break*/, 6];
                                        target = files.find(function (file) { return file.id === Number(downloadMatch[1]); });
                                        return [4 /*yield*/, route.fulfill({
                                                status: 200,
                                                contentType: (target === null || target === void 0 ? void 0 : target.mime_type) || 'text/plain',
                                                body: 'Playwright file content',
                                            })];
                                    case 5:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 6:
                                        if (!(path === '/api/conversations' && method === 'GET')) return [3 /*break*/, 8];
                                        chatType_1 = url.searchParams.get('chat_type');
                                        filtered = chatType_1 ? sessions.filter(function (session) { return session.chat_type === chatType_1; }) : sessions;
                                        return [4 /*yield*/, fulfillJson(route, filtered)];
                                    case 7:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 8:
                                        if (!(path === '/api/conversations' && method === 'POST')) return [3 /*break*/, 10];
                                        body = JSON.parse(request.postData() || '{}');
                                        now = new Date().toISOString();
                                        session = {
                                            id: nextConversationId++,
                                            title: body.chat_type === 'file' ? 'New file conversation' : 'New conversation',
                                            chat_type: body.chat_type,
                                            file_ids: body.file_ids || [],
                                            message_count: 0,
                                            created_at: now,
                                            updated_at: now,
                                        };
                                        sessions.unshift(session);
                                        messagesByConversation[session.id] = [];
                                        return [4 /*yield*/, fulfillJson(route, session, 201)];
                                    case 9:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 10:
                                        detailMatch = path.match(/^\/api\/conversations\/(\d+)$/);
                                        if (!(detailMatch && method === 'GET')) return [3 /*break*/, 14];
                                        conversationId_1 = Number(detailMatch[1]);
                                        session = sessions.find(function (item) { return item.id === conversationId_1; });
                                        if (!!session) return [3 /*break*/, 12];
                                        return [4 /*yield*/, fulfillJson(route, { detail: 'Not found' }, 404)];
                                    case 11:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 12: return [4 /*yield*/, fulfillJson(route, __assign(__assign({}, session), { messages: messagesByConversation[conversationId_1] || [] }))];
                                    case 13:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 14:
                                        addMessageMatch = path.match(/^\/api\/conversations\/(\d+)\/messages$/);
                                        if (!(addMessageMatch && method === 'POST')) return [3 /*break*/, 16];
                                        conversationId_2 = Number(addMessageMatch[1]);
                                        body = JSON.parse(request.postData() || '{}');
                                        now = new Date().toISOString();
                                        message = {
                                            id: nextMessageId++,
                                            role: body.role,
                                            content: body.content,
                                            created_at: now,
                                            updated_at: now,
                                        };
                                        messagesByConversation[conversationId_2] = __spreadArray(__spreadArray([], (messagesByConversation[conversationId_2] || []), true), [message], false);
                                        sessionIndex = sessions.findIndex(function (item) { return item.id === conversationId_2; });
                                        sessions[sessionIndex] = __assign(__assign({}, sessions[sessionIndex]), { message_count: messagesByConversation[conversationId_2].length, updated_at: now });
                                        return [4 /*yield*/, fulfillJson(route, {
                                                message: message,
                                                conversation: sessions[sessionIndex],
                                            }, 201)];
                                    case 15:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 16:
                                        if (!(path === '/api/conversations/chat' && method === 'POST')) return [3 /*break*/, 18];
                                        body = JSON.parse(request.postData() || '{}');
                                        conversationId_3 = body.conversation_id;
                                        now = new Date().toISOString();
                                        assistantContent = body.chat_type === 'file'
                                            ? 'Grounded answer from file context [1.1]'
                                            : 'Normal answer from stream.';
                                        messagesByConversation[conversationId_3] = __spreadArray(__spreadArray([], (messagesByConversation[conversationId_3] || []), true), [
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
                                        ], false);
                                        sessionIndex = sessions.findIndex(function (item) { return item.id === conversationId_3; });
                                        sessions[sessionIndex] = __assign(__assign({}, sessions[sessionIndex]), { message_count: messagesByConversation[conversationId_3].length, updated_at: now });
                                        sseBody = [
                                            'event: status\n',
                                            'data: {"message":"Thinking"}\n\n',
                                            'event: token\n',
                                            "data: ".concat(JSON.stringify({ delta: assistantContent }), "\n\n"),
                                            'event: done\n',
                                            "data: ".concat(JSON.stringify({ citations: body.chat_type === 'file' ? [{ citation_label: '1.1', file_id: 50, file_name: 'notes.txt', page_no: 1, chunk_index: 0 }] : [] }), "\n\n"),
                                        ].join('');
                                        return [4 /*yield*/, route.fulfill({
                                                status: 201,
                                                headers: { 'content-type': 'text/event-stream' },
                                                body: sseBody,
                                            })];
                                    case 17:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 18:
                                        if (!(path === '/api/conversations/deep-research/plan' && method === 'POST')) return [3 /*break*/, 20];
                                        return [4 /*yield*/, fulfillJson(route, {
                                                session_id: 'plan-session-1',
                                                plan: [
                                                    'Collect the latest OCR benchmark changes',
                                                    'Compare PP-OCRv5 against competing pipelines',
                                                ],
                                                message: 'Plan created',
                                            })];
                                    case 19:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 20:
                                        if (!(path === '/api/conversations/deep-research/approve' && method === 'POST')) return [3 /*break*/, 22];
                                        body = JSON.parse(request.postData() || '{}');
                                        session = sessions.find(function (item) { return item.id === 3; });
                                        now = new Date().toISOString();
                                        messagesByConversation[3] = __spreadArray(__spreadArray([], (messagesByConversation[3] || []), true), [
                                            {
                                                id: nextMessageId++,
                                                role: 'assistant',
                                                content: "Deep research final answer based on ".concat(body.approved_plan.length, " steps."),
                                                created_at: now,
                                                updated_at: now,
                                            },
                                        ], false);
                                        if (session) {
                                            session.updated_at = now;
                                            session.message_count = messagesByConversation[3].length;
                                        }
                                        sseBody = [
                                            'event: status\n',
                                            'data: {"message":"Researching sources"}\n\n',
                                            'event: token\n',
                                            "data: ".concat(JSON.stringify({ delta: 'Deep research final answer based on 2 steps.' }), "\n\n"),
                                            'event: done\n',
                                            'data: {"message":"done"}\n\n',
                                        ].join('');
                                        return [4 /*yield*/, route.fulfill({
                                                status: 201,
                                                headers: { 'content-type': 'text/event-stream' },
                                                body: sseBody,
                                            })];
                                    case 21:
                                        _a.sent();
                                        return [2 /*return*/];
                                    case 22: return [4 /*yield*/, route.continue()];
                                    case 23:
                                        _a.sent();
                                        return [2 /*return*/];
                                }
                            });
                        }); })];
                case 2:
                    _d.sent();
                    return [2 /*return*/];
            }
        });
    });
}
(0, test_1.test)('streams a normal chat response end-to-end', function (_a) { return __awaiter(void 0, [_a], void 0, function (_b) {
    var page = _b.page;
    return __generator(this, function (_c) {
        switch (_c.label) {
            case 0: return [4 /*yield*/, primeAuthenticatedApp(page)];
            case 1:
                _c.sent();
                return [4 /*yield*/, mockChatApi(page)];
            case 2:
                _c.sent();
                return [4 /*yield*/, page.goto('/')];
            case 3:
                _c.sent();
                return [4 /*yield*/, page.getByPlaceholder('Ask anything...').fill('What is OCR?')];
            case 4:
                _c.sent();
                return [4 /*yield*/, page.getByPlaceholder('Ask anything...').press('Enter')];
            case 5:
                _c.sent();
                return [4 /*yield*/, (0, test_1.expect)(page.getByText('What is OCR?')).toBeVisible()];
            case 6:
                _c.sent();
                return [4 /*yield*/, (0, test_1.expect)(page.getByText('Normal answer from stream.')).toBeVisible()];
            case 7:
                _c.sent();
                return [2 /*return*/];
        }
    });
}); });
(0, test_1.test)('runs file chat with grounded citations', function (_a) { return __awaiter(void 0, [_a], void 0, function (_b) {
    var page = _b.page;
    return __generator(this, function (_c) {
        switch (_c.label) {
            case 0: return [4 /*yield*/, primeAuthenticatedApp(page, { currentChatId: 2, mode: 'file' })];
            case 1:
                _c.sent();
                return [4 /*yield*/, mockChatApi(page, {
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
                                sas_url: null,
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
                    })];
            case 2:
                _c.sent();
                return [4 /*yield*/, page.goto('/chat-file')];
            case 3:
                _c.sent();
                return [4 /*yield*/, (0, test_1.expect)(page.getByRole('heading', { name: 'notes.txt' })).toBeVisible()];
            case 4:
                _c.sent();
                return [4 /*yield*/, page.getByPlaceholder('Ask anything...').fill('Summarize the attached file')];
            case 5:
                _c.sent();
                return [4 /*yield*/, page.getByPlaceholder('Ask anything...').press('Enter')];
            case 6:
                _c.sent();
                return [4 /*yield*/, (0, test_1.expect)(page.getByText('Grounded answer from file context')).toBeVisible()];
            case 7:
                _c.sent();
                return [4 /*yield*/, (0, test_1.expect)(page.locator('[data-citation-label="1.1"]')).toBeVisible()];
            case 8:
                _c.sent();
                return [2 /*return*/];
        }
    });
}); });
(0, test_1.test)('creates and approves a deep research plan', function (_a) { return __awaiter(void 0, [_a], void 0, function (_b) {
    var deepResearchToggle;
    var page = _b.page;
    return __generator(this, function (_c) {
        switch (_c.label) {
            case 0: return [4 /*yield*/, primeAuthenticatedApp(page, { currentChatId: 3, mode: 'normal' })];
            case 1:
                _c.sent();
                return [4 /*yield*/, mockChatApi(page, {
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
                    })];
            case 2:
                _c.sent();
                return [4 /*yield*/, page.goto('/')];
            case 3:
                _c.sent();
                deepResearchToggle = page.getByRole('button', { name: /^Deep Research$/ });
                return [4 /*yield*/, deepResearchToggle.click()];
            case 4:
                _c.sent();
                return [4 /*yield*/, (0, test_1.expect)(deepResearchToggle).toHaveAttribute('aria-pressed', 'true')];
            case 5:
                _c.sent();
                return [4 /*yield*/, page.getByPlaceholder('Ask anything...').fill('Research the OCR market for me')];
            case 6:
                _c.sent();
                return [4 /*yield*/, page.getByPlaceholder('Ask anything...').press('Enter')];
            case 7:
                _c.sent();
                return [4 /*yield*/, (0, test_1.expect)(page.getByText('Collect the latest OCR benchmark changes')).toBeVisible()];
            case 8:
                _c.sent();
                return [4 /*yield*/, page.getByRole('button', { name: /accept & start research/i }).click()];
            case 9:
                _c.sent();
                return [4 /*yield*/, (0, test_1.expect)(page.getByText('Deep research final answer based on 2 steps.')).toBeVisible()];
            case 10:
                _c.sent();
                return [2 /*return*/];
        }
    });
}); });
