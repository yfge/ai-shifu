// import { MDXEditor } from '@mdxeditor/editor';
import MDXEditor from '@/components/md-editor';
import Markdown from '@/components/markdown'

// import { ALL_PLUGINS } from '@/components/md-editor';
// import { Textarea } from '../ui/textarea';
// import MarkdownEditor from '@/components/markdown-editor'

interface SolideContnetProps {
    content: string;
    profiles: string[];
}

interface SolideContnet {

    isEdit: boolean;
    properties: SolideContnetProps;
    onChange: (properties: SolideContnetProps) => void;
}

export default function SolidContent(props: SolideContnet) {

    const { isEdit } = props;
    if (isEdit) {
        return (
            <MDXEditor
                className="h-60 overflow-auto"
                value={props.properties.content}
                onChange={(value) => {
                    props.onChange({ ...props.properties, content: value })
                }}
            />

        )
    }
    return (

        <Markdown >
            {props.properties.content}
        </Markdown>

    )
}
