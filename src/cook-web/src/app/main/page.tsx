import React from 'react';
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetTrigger,
} from "@/components/ui/sheet";
import {
    Bars3Icon,
    Cog6ToothIcon,
    BookOpenIcon,
    BoltIcon,
    LightBulbIcon,
    ChatBubbleLeftRightIcon,
    ChevronUpIcon,
    ArrowRightOnRectangleIcon,
    HeartIcon,
    MegaphoneIcon,
    DocumentIcon,
    CheckBadgeIcon,
    MapIcon,
    PencilSquareIcon,
    ShieldCheckIcon
} from '@heroicons/react/24/outline';
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import Image from "next/image";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";

const MainInterface = () => {
    const menuItems = [
        { icon: <DocumentIcon className="w-4 h-4" />, label: "剧本", href: "#" },
        { icon: <BookOpenIcon className="w-4 h-4" />, label: "知识库", href: "#" },
        { icon: <BoltIcon className="w-4 h-4" />, label: "模版", href: "#" },
        { icon: <LightBulbIcon className="w-4 h-4" />, label: "灵感", href: "#" },
        { icon: <CheckBadgeIcon className="w-4 h-4" />, label: "晨性实践", href: "#" },
    ];

    const userMenuItems = [
        {
            icon: <PencilSquareIcon className="w-4 h-4" />, label: "个人信息", href: "#"
        },
        { icon: <ShieldCheckIcon className="w-4 h-4" />, label: "安全设置", href: "#" },
        { icon: <MegaphoneIcon className="w-4 h-4" />, label: "最近更新", href: "#" },
        { icon: <MapIcon className="w-4 h-4" />, label: "路线图", href: "#" },
        { icon: <ChatBubbleLeftRightIcon className="w-4 h-4" />, label: "问题反馈", href: "#" },
        { icon: <HeartIcon className="w-4 h-4" />, label: "关注我们", href: "#" },
    ];

    const UserProfileCard = () => (
        <Popover>
            <PopoverTrigger asChild>
                <div className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 cursor-pointer transition-all duration-200 group">
                    <Avatar>
                        <AvatarImage src="https://github.com/shadcn.png" />
                        <AvatarFallback>CN</AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                        <div className="font-medium">Kenrick</div>
                        <div className="text-sm text-gray-500">kenrick.zhou@gmail.com</div>
                    </div>
                    <ChevronUpIcon className="w-4 h-4 text-gray-500 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                </div>
            </PopoverTrigger>
            <PopoverContent side='right' align='end' className="w-64 p-2 border rounded-lg bg-background shadow-md animate-in slide-in-from-bottom-2 duration-200" sideOffset={5}>
                <div className="flex items-center space-x-2 p-2">
                    <Avatar>
                        <AvatarImage src="https://github.com/shadcn.png" />
                        <AvatarFallback>CN</AvatarFallback>
                    </Avatar>
                    <div>
                        <div className="font-medium">Kenrick</div>
                        <div className="text-sm text-gray-500">kenrick.zhou@gmail.com</div>
                    </div>
                </div>
                <hr />
                <div className="space-y-1">
                    {userMenuItems.map((item, index) => (
                        <a
                            key={index}
                            href={item.href}
                            className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-100"
                        >
                            {item.icon}
                            <span>{item.label}</span>
                        </a>
                    ))}
                </div>
                <hr />
                <a
                    href={'/logout'}
                    className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-100"
                >
                    <ArrowRightOnRectangleIcon className="w-4 h-4" />
                    <span>退出登录</span>
                </a>
            </PopoverContent>
        </Popover>
    );

    const SidebarContent = () => (
        <div className="flex flex-col h-full relative shadow-md rounded-2xl bg-background">
            <h1 className="text-xl font-bold p-4">
                <Image
                    className="dark:invert"
                    src="/icons/logo.svg"
                    alt="AI-Shifu"
                    width={140}
                    height={32}
                    priority
                />
            </h1>
            <div className="p-2 flex-1">
                <nav className="space-y-1">
                    {menuItems.map((item, index) => (
                        <a
                            key={index}
                            href={item.href}
                            className="flex items-center space-x-2 px-2 py-2 rounded-lg hover:bg-gray-100"
                        >
                            {item.icon}
                            <span>{item.label}</span>
                        </a>
                    ))}
                </nav>
            </div>

            <div className='p-2 relative'>
                <UserProfileCard />
            </div>
        </div>
    );

    return (
        <div className="h-screen flex bg-stone-50">
            {/* Desktop Sidebar */}
            <div className="hidden md:flex w-64 border-r flex-col p-2">
                <SidebarContent />
            </div>

            {/* Mobile Header */}
            <div className="md:hidden w-full border-b p-4">
                <div className="flex items-center justify-between">
                    <Sheet>
                        <SheetTrigger asChild>
                            <Button variant="ghost" size="icon">
                                <Bars3Icon className="h-6 w-6" />
                            </Button>
                        </SheetTrigger>
                        <SheetContent side="left" className="w-64 p-0">
                            <SidebarContent />
                        </SheetContent>
                    </Sheet>
                    <h1 className="text-xl font-bold">首页</h1>
                    <div className="w-6" /> {/* Spacer for centering */}
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 p-6">
                <div className="max-w-4xl mx-auto">
                    {/* Participation Section */}
                    <div className="mb-8">
                        <h2 className="text-lg font-semibold mb-4">参与社区</h2>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {/* Note: Using specific icons for social media */}
                            <a href="#" className="flex items-center space-x-2 p-4 rounded-lg border hover:bg-gray-50">
                                <ChatBubbleLeftRightIcon className="w-5 h-5" />
                                <span>Github</span>
                            </a>
                            <a href="#" className="flex items-center space-x-2 p-4 rounded-lg border hover:bg-gray-50">
                                <ChatBubbleLeftRightIcon className="w-5 h-5" />
                                <span>Discord</span>
                            </a>
                            <a href="#" className="flex items-center space-x-2 p-4 rounded-lg border hover:bg-gray-50">
                                <ChatBubbleLeftRightIcon className="w-5 h-5" />
                                <span>Weibo</span>
                            </a>
                            <a href="#" className="flex items-center space-x-2 p-4 rounded-lg border hover:bg-gray-50">
                                <ChatBubbleLeftRightIcon className="w-5 h-5" />
                                <span>X</span>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MainInterface;