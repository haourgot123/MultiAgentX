import { useState, useRef } from "react"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Check, X, Edit2, Save, Plus, Trash2 } from "lucide-react"

interface PlanApprovalModalProps {
    isOpen: boolean
    plan: string[]
    sessionId: string
    onApprove: (approvedPlan: string[], sessionId: string) => Promise<void>
    onCancel: () => void
}

export function PlanApprovalModal({
    isOpen,
    plan,
    sessionId,
    onApprove,
    onCancel,
}: PlanApprovalModalProps) {
    const [isEditing, setIsEditing] = useState(false)
    const [editedPlan, setEditedPlan] = useState<string[]>(plan)
    const [isSubmitting, setIsSubmitting] = useState(false)
    // Track if approval was triggered to avoid firing onCancel when modal closes programmatically
    const approvedRef = useRef(false)

    const handleApprove = async () => {
        approvedRef.current = true
        setIsSubmitting(true)
        try {
            await onApprove(isEditing ? editedPlan : plan, sessionId)
        } finally {
            setIsSubmitting(false)
            approvedRef.current = false
        }
    }

    const handleEditToggle = () => {
        if (isEditing) {
            setEditedPlan([...plan])
        }
        setIsEditing(!isEditing)
    }

    const handleQuestionChange = (index: number, value: string) => {
        const newPlan = [...editedPlan]
        newPlan[index] = value
        setEditedPlan(newPlan)
    }

    const handleAddQuestion = () => {
        setEditedPlan([...editedPlan, ""])
    }

    const handleRemoveQuestion = (index: number) => {
        const newPlan = editedPlan.filter((_, i) => i !== index)
        setEditedPlan(newPlan)
    }

    const currentPlan = isEditing ? editedPlan : plan

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && !approvedRef.current && onCancel()}>
            <DialogContent className="max-w-2xl max-h-[80vh] bg-white rounded-xl">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
                            Deep Research Plan
                        </Badge>
                    </DialogTitle>
                    <DialogDescription>
                        Review the research plan below. You can accept it as-is or edit the questions before proceeding.
                    </DialogDescription>
                </DialogHeader>

                <ScrollArea className="flex-1 pr-4 max-h-[50vh]">
                    <div className="space-y-3 py-4">
                        {currentPlan.map((question, index) => (
                            <div key={index} className="flex items-start gap-2">
                                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-medium mt-2">
                                    {index + 1}
                                </div>
                                {isEditing ? (
                                    <div className="flex-1 flex gap-2">
                                        <Textarea
                                            value={question}
                                            onChange={(e) => handleQuestionChange(index, e.target.value)}
                                            className="flex-1 resize-none"
                                            rows={2}
                                            placeholder="Enter research question..."
                                        />
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50"
                                            onClick={() => handleRemoveQuestion(index)}
                                            disabled={editedPlan.length <= 1}
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                ) : (
                                    <div className="flex-1 p-3 rounded-lg bg-surface border border-border">
                                        <p className="text-sm text-text-primary">{question}</p>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </ScrollArea>

                {isEditing && (
                    <div className="pt-2">
                        <Button
                            variant="outline"
                            size="sm"
                            className="w-full"
                            onClick={handleAddQuestion}
                        >
                            <Plus className="h-4 w-4 mr-2" />
                            Add Question
                        </Button>
                    </div>
                )}

                <DialogFooter className="gap-2 sm:gap-0">
                    <Button
                        variant="outline"
                        onClick={onCancel}
                        disabled={isSubmitting}
                        className="rounded-lg"
                    >
                        <X className="h-4 w-4 mr-2" />
                        Cancel
                    </Button>
                    
                    <Button
                        variant="outline"
                        onClick={handleEditToggle}
                        disabled={isSubmitting}
                        className="rounded-lg"
                    >
                        {isEditing ? (
                            <>
                                <X className="h-4 w-4 mr-2" />
                                Cancel Edit
                            </>
                        ) : (
                            <>
                                <Edit2 className="h-4 w-4 mr-2" />
                                Edit Plan
                            </>
                        )}
                    </Button>
                    
                    <Button
                        className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                        onClick={handleApprove}
                        disabled={isSubmitting || (isEditing && editedPlan.some(q => !q.trim()))}
                    >
                        {isSubmitting ? (
                            <>
                                <div className="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                Starting...
                            </>
                        ) : (
                            <>
                                {isEditing ? <Save className="h-4 w-4 mr-2" /> : <Check className="h-4 w-4 mr-2" />}
                                {isEditing ? "Save & Start Research" : "Accept & Start Research"}
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}