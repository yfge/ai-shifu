"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "@/hooks/use-toast"
import { Loader2 } from "lucide-react"

interface FeedbackFormProps {
  onSuccess?: () => void
  onLoginClick?: () => void
  isDialog?: boolean
}

export function FeedbackForm({ onSuccess, onLoginClick, isDialog = false }: FeedbackFormProps) {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [email, setEmail] = useState("")
  const [content, setContent] = useState("")

  const handleSubmit = async () => {
    if (!email || !content) {
      toast({
        title: "请填写所有字段",
        variant: "destructive",
      })
      return
    }

    try {
      setIsLoading(true)
      // 模拟提交反馈
      await new Promise((resolve) => setTimeout(resolve, 1000))

      toast({
        title: "反馈提交成功",
        description: "感谢您的反馈，我们会尽快处理",
      })

      if (onSuccess) {
        onSuccess()
      } else {
        router.push("/auth/login")
      }
    } catch (error: any) {
      toast({
        title: "提交失败",
        description: error.message,
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogin = () => {
    if (onLoginClick) {
      onLoginClick()
    } else if (!isDialog) {
      router.push("/auth/login")
    }
  }

  return (
    <Card className={isDialog ? "border-0 shadow-none" : ""}>
      <CardHeader>
        <CardTitle className="text-2xl text-center">提交反馈</CardTitle>
        <CardDescription className="text-center">请告诉我们您遇到的问题或建议</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">您的邮箱</Label>
          <Input
            id="email"
            type="email"
            placeholder="请输入您的邮箱"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="content">反馈内容</Label>
          <Textarea
            id="content"
            placeholder="请详细描述您遇到的问题或建议"
            rows={5}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={isLoading}
          />
        </div>
        <Button className="w-full" onClick={handleSubmit} disabled={isLoading}>
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
          提交反馈
        </Button>
      </CardContent>
      <CardFooter className="flex justify-center">
        <Button variant="link" onClick={handleLogin}>
          返回登录
        </Button>
      </CardFooter>
    </Card>
  )
}
