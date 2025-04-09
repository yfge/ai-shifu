import React, { useState } from "react";
import { Copy, Check, Upload, SlidersVertical } from "lucide-react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogTrigger
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";

// Define the validation schema using Zod
const courseSchema = z.object({
    previewUrl: z.string(),
    learningUrl: z.string(),
    courseName: z.string()
        .min(1, "课程名称不能为空")
        .max(50, "课程名称不能超过50字"),
    courseDescription: z.string()
        .min(1, "课程简介不能为空")
        .max(300, "课程简介不能超过300字"),
    selectedModel: z.string().min(1, "请选择模型"),
    price: z.string()
        .min(1, "价格不能为空")
        .regex(/^\d+(\.\d{1,2})?$/, "价格必须是有效的数字格式"),
});

export default function CourseCreationDialog() {
    const [open, setOpen] = useState(false);
    const [keywords, setKeywords] = useState(["AIGC"]);
    const [courseImage, setCourseImage] = useState<File | null>(null);
    const [imageError, setImageError] = useState("");
    const [copying, setCopying] = useState({
        previewUrl: false,
        learningUrl: false
    });

    // Initialize the form with react-hook-form and zod resolver
    const form = useForm({
        resolver: zodResolver(courseSchema),
        defaultValues: {
            previewUrl: "www.www.com",
            learningUrl: "www.xxxx.com",
            courseName: "字符串",
            courseDescription: "字符串",
            selectedModel: "GPT-4o-2024-5-13",
            price: ""
        },
    });

    // Handle copy to clipboard
    const handleCopy = (field) => {
        navigator.clipboard.writeText(form.getValues(field));
        setCopying({ ...copying, [field]: true });

        setTimeout(() => {
            setCopying({ ...copying, [field]: false });
        }, 2000);
    };

    // Handle keyword addition
    const handleAddKeyword = () => {
        const keyword = (document.getElementById("keywordInput") as any)?.value.trim();
        if (keyword && !keywords.includes(keyword)) {
            setKeywords([...keywords, keyword]);
            (document.getElementById("keywordInput") as any).value = "";
        }
    };

    // Handle keyword removal
    const handleRemoveKeyword = (keyword) => {
        setKeywords(keywords.filter(k => k !== keyword));
    };

    // Handle image upload
    const handleImageUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            // Validate file size
            if (file.size > 2 * 1024 * 1024) {
                setImageError("文件大小不能超过2MB");
                setCourseImage(null);
                return;
            }

            // Validate file type
            if (!['image/jpeg', 'image/png'].includes(file.type)) {
                setImageError("只支持JPG和PNG格式");
                setCourseImage(null);
                return;
            }

            setCourseImage(file);
            setImageError("");
        }
    };

    // Handle form submission
    const onSubmit = (data) => {
        // Combine form data with keywords and image
        const fullFormData = {
            ...data,
            keywords,
            courseImage
        };

        console.log("Form submitted:", fullFormData);
        // Here you would typically make an API call to save the data
        setOpen(false);
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <SlidersVertical className='cursor-pointer h-4 w-4 text-gray-500' />
            </DialogTrigger>
            <DialogContent className="sm:max-w-md md:max-w-lg lg:max-w-xl">
                <DialogHeader>
                    <DialogTitle className="text-lg font-medium">创建新课程</DialogTitle>
                </DialogHeader>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)}>
                        <div className="h-[500px] py-2 px-4 overflow-auto space-y-2">
                            {/* Preview URL */}
                            <FormField
                                control={form.control}
                                name="previewUrl"
                                render={({ field }) => (
                                    <FormItem className="grid grid-cols-4 items-center gap-2 space-y-0">
                                        <FormLabel className="text-right text-sm">预览地址</FormLabel>
                                        <div className="col-span-3 flex items-center space-x-2">
                                            <FormControl>
                                                <span className="px-1 w-full overflow-hidden text-ellipsis whitespace-nowrap">
                                                    {field.value}
                                                </span>
                                            </FormControl>
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => handleCopy("previewUrl")}
                                            >
                                                {copying.previewUrl ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                            </Button>
                                        </div>
                                        <div className="col-span-3 col-start-2">
                                            <FormMessage />
                                        </div>
                                    </FormItem>
                                )}
                            />

                            {/* Learning URL */}
                            <FormField
                                control={form.control}
                                name="learningUrl"
                                render={({ field }) => (
                                    <FormItem className="grid grid-cols-4 items-center gap-2 space-y-0">
                                        <FormLabel className="text-right text-sm">学习地址</FormLabel>
                                        <div className="col-span-3 flex items-center space-x-2">
                                            <FormControl>
                                                <span className="px-1 w-full overflow-hidden text-ellipsis whitespace-nowrap">
                                                    {field.value}
                                                </span>
                                            </FormControl>
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => handleCopy("learningUrl")}
                                            >
                                                {copying.learningUrl ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                            </Button>
                                        </div>
                                        <div className="col-span-3 col-start-2">
                                            <FormMessage />
                                        </div>
                                    </FormItem>
                                )}
                            />

                            {/* Course Name */}
                            <FormField
                                control={form.control}
                                name="courseName"
                                render={({ field }) => (
                                    <FormItem className="grid grid-cols-4 items-start gap-4 space-y-0">
                                        <FormLabel className="text-right text-sm pt-2">课程名称</FormLabel>
                                        <div className="col-span-3">
                                            <FormControl>
                                                <Input {...field} maxLength={50} placeholder="限制50字以内" />
                                            </FormControl>
                                            <p className="text-xs text-gray-500 mt-1">
                                                {field.value.length}/50
                                            </p>
                                            <FormMessage />
                                        </div>
                                    </FormItem>
                                )}
                            />

                            {/* Course Description */}
                            <FormField
                                control={form.control}
                                name="courseDescription"
                                render={({ field }) => (
                                    <FormItem className="grid grid-cols-4 items-start gap-4">
                                        <FormLabel className="text-right text-sm pt-2">课程简介</FormLabel>
                                        <div className="col-span-3">
                                            <FormControl>
                                                <Textarea
                                                    {...field}
                                                    maxLength={300}
                                                    placeholder="限制300字以内"
                                                    rows={4}
                                                />
                                            </FormControl>
                                            <p className="text-xs text-gray-500 mt-1">
                                                {field.value.length}/300
                                            </p>
                                            <FormMessage />
                                        </div>
                                    </FormItem>
                                )}
                            />

                            {/* Keywords */}
                            <div className="grid grid-cols-4 items-start gap-4">
                                <label className="text-right text-sm pt-2 font-semibold">关键词</label>
                                <div className="col-span-3">
                                    <div className="flex flex-wrap gap-2 mb-2">
                                        {keywords.map((keyword, index) => (
                                            <Badge
                                                key={index}
                                                variant="secondary"
                                                className="flex items-center gap-1"
                                            >
                                                {keyword}
                                                <button
                                                    type="button"
                                                    onClick={() => handleRemoveKeyword(keyword)}
                                                    className="text-xs ml-1 hover:text-red-500"
                                                >
                                                    ×
                                                </button>
                                            </Badge>
                                        ))}
                                    </div>
                                    <div className="flex gap-2">
                                        <Input
                                            id="keywordInput"
                                            placeholder="输入关键词"
                                            className="flex-grow h-8"
                                        />
                                        <Button
                                            type="button"
                                            className="h-8"
                                            onClick={handleAddKeyword}
                                            variant="outline"
                                            size="sm"
                                        >
                                            + 添加关键字
                                        </Button>
                                    </div>
                                </div>
                            </div>

                            {/* Course Image */}
                            <div className="grid grid-cols-4 items-start gap-4">
                                <label className="text-right text-sm pt-2 font-semibold">课程头像</label>
                                <div className="col-span-3">
                                    <div
                                        className="border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer"
                                        onClick={() => document.getElementById("imageUpload")?.click()}
                                    >
                                        <Upload className="h-8 w-8 mb-2 text-gray-400" />
                                        <p className="text-sm text-center">上传</p>
                                        <input
                                            id="imageUpload"
                                            type="file"
                                            accept="image/jpeg,image/png"
                                            onChange={handleImageUpload}
                                            className="hidden"
                                        />
                                    </div>
                                    <p className="text-xs text-gray-500 mt-1">
                                        支持 JPG、PNG 格式，文件小于 2MB
                                    </p>
                                    {imageError && (
                                        <p className="text-red-500 text-xs mt-1">{imageError}</p>
                                    )}
                                    {courseImage && (
                                        <p className="text-green-500 text-xs mt-1">
                                            已选择: {courseImage?.name}
                                        </p>
                                    )}
                                </div>
                            </div>

                            {/* Model Selection */}
                            <FormField
                                control={form.control}
                                name="selectedModel"
                                render={({ field }) => (
                                    <FormItem className="grid grid-cols-4 items-center gap-4">
                                        <FormLabel className="text-right text-sm">选择模型</FormLabel>
                                        <div className="col-span-3">
                                            <Select
                                                onValueChange={field.onChange}
                                                defaultValue={field.value}
                                            >
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="选择模型" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value="GPT-4o-2024-5-13">GPT-4o-2024-5-13</SelectItem>
                                                    <SelectItem value="GPT-4">GPT-4</SelectItem>
                                                    <SelectItem value="GPT-3.5-Turbo">GPT-3.5-Turbo</SelectItem>
                                                    <SelectItem value="claude-3-opus">Claude 3 Opus</SelectItem>
                                                    <SelectItem value="claude-3-sonnet">Claude 3 Sonnet</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </div>
                                    </FormItem>
                                )}
                            />

                            {/* Price */}
                            <FormField
                                control={form.control}
                                name="price"
                                render={({ field }) => (
                                    <FormItem className="grid grid-cols-4 items-center gap-4">
                                        <FormLabel className="text-right text-sm">价格</FormLabel>
                                        <div className="col-span-3">
                                            <FormControl>
                                                <Input {...field} placeholder="数字" />
                                            </FormControl>
                                            <FormMessage />
                                        </div>
                                    </FormItem>
                                )}
                            />

                        </div>
                        <DialogFooter className="sm:justify-end pt-4">
                            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                                取消
                            </Button>
                            <Button
                                type="submit"
                                className="bg-purple-600 hover:bg-purple-700 text-white"
                            >
                                保存
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}
