// Displays output text on the SaveWorkflowNode as an additional input.

import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

// ComfyUI's internal name of the SaveWorkflowNode. This should match the value given in "__init__.py".
const NODE_CLASS_NAME = "brkp_SaveWorkflow";

// The output message from SaveWorkflowNode will be passed to us in this key (see "nodes/save_workflow.py").
const OUTPUT_TEXT_KEY = "dispText"

// Name of the function in SaveWorkflowNode's class that we hook into to execute our custom JavaScript.
const HOOKED_FUNCTION = "onExecuted"

// Output text is actually added as a ComfyUI node input. This will be the name of that input parameter.
const ADDITIONAL_INPUT_NAME = "_displayed_text";

// ComfyUI input type, used to select the relevant "widget" constructor.
const STRING_INPUT_TYPE = "STRING";

// Used to set the HTML attribute of the output text box.
const HTML_ELEMENT_READONLY_ATTRIBUTE = "readonly";

// Used to customize the CSS style attributes of the output text box.
const OUTPUT_TEXT_BOX_STYLE = {
    "opacity": 0.75,
};

// Helper function to hook a method in a class prototype that does not return anything.
function hookPrototypeMethod(Class, methodName, hookFn) {
    const original = Class.prototype[methodName];
  
    if (original && typeof original !== "function") {
        throw new Error(`Failed to hook ${methodName}, it is not a function!`);
    }
  
    Class.prototype[methodName] = function (...args) {
        original?.call(this, ...args);
        hookFn(this, ...args);
    };
}

// Displays the output text from SaveWorkflowNode to the ComfyUI user interface.
// This JavaScript function is to be executed after the Python SaveWorkflowNode is executed.
function onSaveWorkflow(node, uiObject) {
    const uiMessage = uiObject[OUTPUT_TEXT_KEY][0];

    if (uiObject?.[OUTPUT_TEXT_KEY]?.length > 0) {
        // An input parameter to a node is also known as a "widget" for some reason
        const inputParameters = node?.widgets;
        const additionalInput = inputParameters?.find(input => input.name === ADDITIONAL_INPUT_NAME);

        if (additionalInput) {
            // "widget" for output already exists (maybe from a previous run), simply update its value
            additionalInput.value = uiMessage;
        } else {
            // Select the correct constructor from ComfyWidgets
            const constructWidgetFn = ComfyWidgets[STRING_INPUT_TYPE];
            // Construct a new input parameter in the node to display output
            // (set output message as the default value for the new parameter)
            const newInputParam = constructWidgetFn(
                /* node:      */ node,
                /* inputName: */ ADDITIONAL_INPUT_NAME,
                /* inputData: */ [STRING_INPUT_TYPE, { multiline: true, default: uiMessage }]
            );

            // Set HTML/CSS properties of the output text box
            const innerWidget = newInputParam.widget;
            const outputTextBox = innerWidget.inputEl;
            outputTextBox.setAttribute(HTML_ELEMENT_READONLY_ATTRIBUTE, true);
            for (const [key, value] of Object.entries(OUTPUT_TEXT_BOX_STYLE)) {
                outputTextBox.style[key] = value;
            }
        }
    } else {
        console.error(`Could not find ${OUTPUT_TEXT_KEY} in object returned from SaveWorkflowNode!`);
        console.log(`SaveWorkflowNode: ${uiMessage}`);
    }
}

app.registerExtension({
    name: "brkp.SaveWorkflowNode",
    beforeRegisterNodeDef: async (NodeType, nodeData) => {
        if (nodeData.name !== NODE_CLASS_NAME) {
            return;
        }

        // Hook SaveWorkflowNode's onExecuted() to display the output message
        hookPrototypeMethod(NodeType, HOOKED_FUNCTION, onSaveWorkflow);
    },
});
