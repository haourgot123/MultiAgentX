import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { MessageBubble } from '@/components/chat/MessageBubble'

const windowOpenMock = vi.fn()

vi.stubGlobal('open', windowOpenMock)

describe('MessageBubble', () => {
    it('renders user messages on the reversed row layout', () => {
        const { container } = render(
            <MessageBubble
                message={{
                    id: 1,
                    role: 'user',
                    content: 'What is PaddleOCR?',
                    timestamp: Date.parse('2026-04-15T10:00:00Z'),
                }}
            />
        )

        expect(screen.getByText('What is PaddleOCR?')).toBeInTheDocument()
        expect(container.firstElementChild).toHaveClass('flex-row-reverse')
    })

    it('renders assistant messages on the normal row layout', () => {
        const { container } = render(
            <MessageBubble
                message={{
                    id: 2,
                    role: 'assistant',
                    content: 'PaddleOCR is an open-source OCR toolkit.',
                    timestamp: Date.parse('2026-04-15T10:01:00Z'),
                }}
            />
        )

        expect(screen.getByText('PaddleOCR is an open-source OCR toolkit.')).toBeInTheDocument()
        expect(container.firstElementChild).toHaveClass('flex-row')
        expect(container.firstElementChild).not.toHaveClass('flex-row-reverse')
    })

    it('renders unresolved numbered citations as non-interactive badges', () => {
        render(
            <MessageBubble
                message={{
                    id: 3,
                    role: 'assistant',
                    content: 'This answer cites a source [1] but no references section is available.',
                    timestamp: Date.parse('2026-04-15T10:02:00Z'),
                }}
            />
        )

        const citationBadge = screen.getAllByText('1')[0]

        expect(citationBadge).toHaveAttribute('aria-disabled', 'true')
        expect(citationBadge).not.toHaveAttribute('href')

        fireEvent.click(citationBadge)

        expect(windowOpenMock).not.toHaveBeenCalled()
    })

    it('opens resolved numbered citations when a source is available', () => {
        render(
            <MessageBubble
                message={{
                    id: 4,
                    role: 'assistant',
                    content: 'This answer cites a source [1].\n\n## Sources\n[1] [Example](https://example.com)',
                    timestamp: Date.parse('2026-04-15T10:03:00Z'),
                }}
            />
        )

        const citationBadge = screen.getAllByText('1')[0]

        expect(citationBadge).toHaveAttribute('href', 'https://example.com')
        expect(citationBadge).toHaveAttribute('target', '_blank')

        fireEvent.click(citationBadge)

        expect(windowOpenMock).toHaveBeenCalledWith('https://example.com', '_blank', 'noreferrer')
    })

    it('shows the source link when hovering a resolved citation badge', async () => {
        const user = userEvent.setup()

        render(
            <MessageBubble
                message={{
                    id: 5,
                    role: 'assistant',
                    content: 'Hover this citation [1].\n\n## Sources\n[1] [Example](https://example.com)',
                    timestamp: Date.parse('2026-04-15T10:04:00Z'),
                }}
            />
        )

        const citationBadge = screen.getAllByText('1')[0]
        await user.hover(citationBadge)

        expect((await screen.findAllByText('https://example.com')).length).toBeGreaterThan(0)
        expect(screen.getAllByText('Click to open source').length).toBeGreaterThan(0)
    })

    it('preserves inline numeric markdown citations as clickable links', () => {
        render(
            <MessageBubble
                message={{
                    id: 6,
                    role: 'assistant',
                    content: 'Deep research supports this claim [1](https://example.com).',
                    timestamp: Date.parse('2026-04-15T10:05:00Z'),
                }}
            />
        )

        const citationLink = screen.getByRole('link', { name: '1' })

        expect(citationLink).toHaveAttribute('href', 'https://example.com')
        expect(citationLink).toHaveAttribute('target', '_blank')
    })

    it('resolves citations from numbered sources headings like 7. Sources', async () => {
        const user = userEvent.setup()

        render(
            <MessageBubble
                message={{
                    id: 7,
                    role: 'assistant',
                    content: 'A supported claim [11].\n\n### 7. Sources\n[11] [Yahoo Finance](https://finance.yahoo.com)',
                    timestamp: Date.parse('2026-04-15T10:06:00Z'),
                }}
            />
        )

        const citationBadge = screen.getAllByText('11')[0]

        fireEvent.click(citationBadge)
        expect(windowOpenMock).toHaveBeenCalledWith('https://finance.yahoo.com', '_blank', 'noreferrer')

        await user.hover(citationBadge)
        expect((await screen.findAllByText('https://finance.yahoo.com')).length).toBeGreaterThan(0)
    })

    it('resolves citations when the references section uses ordered-list numbering', async () => {
        const user = userEvent.setup()

        render(
            <MessageBubble
                message={{
                    id: 8,
                    role: 'assistant',
                    content: 'A supported claim [2].\n\n## References\n1. [OpenAI](https://openai.com)\n2. [Anthropic](https://anthropic.com)',
                    timestamp: Date.parse('2026-04-15T10:07:00Z'),
                }}
            />
        )

        const citationBadge = screen.getAllByText('2')[0]

        fireEvent.click(citationBadge)
        expect(windowOpenMock).toHaveBeenCalledWith('https://anthropic.com', '_blank', 'noreferrer')

        await user.hover(citationBadge)
        expect((await screen.findAllByText('https://anthropic.com')).length).toBeGreaterThan(0)
    })

    it('resolves citations from Vietnamese Nguồn headings', async () => {
        const user = userEvent.setup()

        render(
            <MessageBubble
                message={{
                    id: 9,
                    role: 'assistant',
                    content: 'Một nhận định có dẫn nguồn [3].\n\n### 7. Nguồn\n[1] [Statista](https://www.statista.com)\n[2] [Gartner](https://www.gartner.com)\n[3] [ManpowerGroup](https://www.manpowergroup.com)',
                    timestamp: Date.parse('2026-04-15T10:08:00Z'),
                }}
            />
        )

        const citationBadge = screen.getAllByText('3')[0]

        fireEvent.click(citationBadge)
        expect(windowOpenMock).toHaveBeenCalledWith('https://www.manpowergroup.com', '_blank', 'noreferrer')

        await user.hover(citationBadge)
        expect((await screen.findAllByText('https://www.manpowergroup.com')).length).toBeGreaterThan(0)
    })
})
