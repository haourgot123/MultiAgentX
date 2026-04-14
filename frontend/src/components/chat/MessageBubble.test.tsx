import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { MessageBubble } from '@/components/chat/MessageBubble'

vi.mock('react-markdown', () => ({
    default: ({ children }: { children: string }) => <div>{children}</div>,
}))

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
})