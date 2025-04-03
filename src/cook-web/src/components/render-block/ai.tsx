
// import { MDXEditor } from '@mdxeditor/editor';
import MDXEditor from '@/components/md-editor';
import Markdown from '@/components/markdown'

// import { Textarea } from "../ui/textarea";
// import { Textarea } from "../ui/textarea";
// import MarkdownEditor from '@/components/markdown-editor'


interface AIBlockProps {
    prompt: string;
    profiles: string[];
    model: string;
    temprature: string;
    other_conf: string;
}

interface AIBlock {
    isEdit: boolean;
    properties: AIBlockProps;
    onChange: (properties: AIBlockProps) => void;
}

export default function AI(props: AIBlock) {

    if (props.properties.content) {
        props.properties.prompt = props.properties.content;
        delete props.properties.content;
    }

    const { isEdit } = props;
    if (isEdit) {
        return (
            <MDXEditor
                className="h-60 overflow-auto markdown"
                value={props.properties.prompt}
                onChange={(value) => {
                    props.onChange({ ...props.properties, prompt: value })
                }}
            />
        )
    }
    return (
        <Markdown >
            {props.properties.prompt}
        </Markdown>
    )
}
