import React, { useEffect, useState } from 'react'

import OutlineSelector from '@/components/outline-selector'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { useScenario } from '@/store'
import { Outline } from '@/types/scenario'
import api from '@/api'
import { Button } from '../ui/button'

interface ColorSetting {
    color: string;
    text_color: string;
}

interface ProfileItemDefination {
    color_setting: ColorSetting;
    profile_key: string;
    profile_id: string;
}


interface GotoProps {
    properties: {
        "goto_settings": {
            "items": {
                "value": string,
                "type": string,
                "goto_id": string
            }[],
            "profile_key": string
        },
        "button_name": string,
        "button_key": string
    }
    onChange: (properties: any) => void
}

export default function Goto(props: GotoProps) {
    const { properties } = props
    const {
        chapters,
        currentScenario
    } = useScenario();

    const [profileItemDefinations, setProfileItemDefinations] = useState<ProfileItemDefination[]>([]);
    const [profileItemId, setProfileItemId] = useState("");
    const [profileItemName, setProfileItemName] = useState("");
    const [tempGotoSettings, setTempGotoSettings] = useState(properties.goto_settings);

    useEffect(() => {
        loadProfileItemDefinations();
    }, [profileItemId])

    const onNodeSelect = (index: number, node: Outline) => {
        setTempGotoSettings({
            ...tempGotoSettings,
            items: tempGotoSettings.items.map((item, i) => {
                if (i === index) {
                    return {
                        ...item,
                        goto_id: node.id
                    }
                }
                return item
            })
        });
    }

    const handleConfirm = () => {
        props.onChange({
            ...properties,
            goto_settings: tempGotoSettings
        });
    }

    const loadProfileItemDefinations = async () => {
        const list = await api.getProfileItemDefinitions({
            parent_id: currentScenario?.id
        })
        setProfileItemDefinations(list)
        setProfileItemName(list.find((item) => item.profile_id == profileItemId)?.profile_key || "")
    }

    useEffect(() => {
        if (profileItemDefinations.length > 0) {
            const selectedItem = profileItemDefinations.find((item) => item.profile_key === properties.goto_settings.profile_key);
            if (selectedItem) {
                setProfileItemId(selectedItem.profile_id);
            }
        }
    }, [profileItemDefinations])


    const init = async () => {
        await loadProfileItemDefinations();
    }
    const loadProfileItem = async () => {
        const list = await api.getProfileItemOptionList({
            parent_id: profileItemId
        })
        setTempGotoSettings({
            ...tempGotoSettings,
            items: list.map((item) => {
                return {
                    value: item.value,
                    goto_id: tempGotoSettings.items.find((i) => i.value === item.value)?.goto_id || "",
                    type: "goto"
                }
            })
        });
    }
    useEffect(() => {
        init();
    }, [])
    useEffect(() => {
        if (profileItemId) {
            loadProfileItem();
        }
    }, [profileItemId])
    return (
        <div className='flex flex-col space-y-1'>
            <div className='flex flex-row items-center space-x-1'>
                <div className='flex flex-row whitespace-nowrap w-[70px] shrink-0'>
                    变量选择：
                </div>
                <Select value={profileItemId} defaultValue={profileItemId} onValueChange={(value) => {
                    const selectedItem = profileItemDefinations.find((item) => item.profile_id === value);
                    if (selectedItem) {
                        setProfileItemId(value)
                        setProfileItemName(selectedItem.profile_key)
                        setTempGotoSettings({
                            ...tempGotoSettings,
                            profile_key: selectedItem.profile_key
                        });
                    }
                }} onOpenChange={(open) => {
                    if (open) {
                        loadProfileItemDefinations();
                    }
                }}>
                    <SelectTrigger className=" h-8 w-[170px]">
                        <SelectValue defaultValue={profileItemId} placeholder="选择变量" >
                            {profileItemName}
                        </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                        {
                            profileItemDefinations?.map((item) => {
                                return <SelectItem key={item.profile_key} value={item.profile_id} >{item.profile_key}</SelectItem>
                            })
                        }
                    </SelectContent>
                </Select>
            </div>
            <div className='flex flex-row items-start py-2'>
                <div className='flex flex-row whitespace-nowrap w-[70px] shrink-0'>
                    跳转位置：
                </div>
                <div className='flex flex-col space-y-1 '>
                    {
                        tempGotoSettings.items.map((item, index) => {
                            return (
                                <div className='flex flex-row items-center space-x-2' key={`${item.value}-${index}`}>
                                    <span className='w-40'>{item.value}</span>
                                    <span className='px-2'>跳转到</span>
                                    <span>
                                        <OutlineSelector value={item.goto_id} chapters={chapters} onSelect={onNodeSelect.bind(null, index)} />
                                    </span>
                                </div>
                            )
                        })
                    }
                </div>
            </div>
            <div className='flex flex-row items-center'>
                <span className='flex flex-row items-center whitespace-nowrap w-[70px] shrink-0'>
                </span>
                <Button
                    className='h-8 w-20'
                    onClick={handleConfirm}
                >
                    完成
                </Button>
            </div>
        </div>
    )
}
