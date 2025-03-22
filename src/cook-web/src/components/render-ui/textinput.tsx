
import React from 'react'
import { Input } from '../ui/input'

interface ButtonProps {
    properties: {
        "prompt": {
            "properties": {
                "prompt": string,
                "profiles": string[],
                "model": string,
                "temprature": string,
                "other_conf": string,
            },
            "type": string
        },
        "input_name": string,
        "input_key": string,
        "input_placeholder": string
    }
    onChange: (properties: any) => void
}

export default function TextInput(props: ButtonProps) {
    const { properties } = props

    const onValueChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        console.log('onChange', properties);

    }
    return (
        <div className='flex flex-row space-x-1 items-center'>

        </div>
    )
}
