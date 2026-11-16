"""medxpert-ortho-mcp — 骨科器械检测对接 MCP Server（stdio，纯标准库，零依赖）。

本包是四个 MedXpert 专家包长期引用、此前一直不存在的共享连接器。
现在它是一个真实可安装的 MCP server：`uvx medxpert-ortho-mcp` 即起。

数据说明：包内 datasets/ 全部为**示例数据**，用于演示工具语义与返回结构，
不构成资质目录、报价承诺或法规结论；正式使用须替换为你自己的数据目录
（环境变量 ORTHO_DATA_DIR）。
"""

__version__ = "0.1.1"
