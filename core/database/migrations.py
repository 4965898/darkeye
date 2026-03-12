#这里是迁移数据库的，在软件启动的时候检测数据库与软件所需要的数据库版本是否一致，否则进行升级
import sqlite3
from sqlite3 import Connection
from .connection import get_connection
import logging

def get_db_version(conn:Connection):
    cur = conn.execute("SELECT version FROM db_version ORDER BY applied_at DESC LIMIT 1;")
    row = cur.fetchone()
    return row[0] if row else None

def set_db_version(conn:Connection, version:str, description:str=""):
    conn.execute(
        "INSERT INTO db_version (version, description) VALUES (?, ?)",
        (version, description)
    )
    conn.commit()


from config import REQUIRED_PRIVATE_DB_VERSION,REQUIRED_PUBLIC_DB_VERSION,DATABASE,PRIVATE_DATABASE

def upgrade_public_db(conn, current_version):
    """执行数据库升级逻辑"""
    logging.info(f"公共数据库版本从 {current_version or '无版本'} 升级到 {REQUIRED_PUBLIC_DB_VERSION}")
    #当版本库不一致时就一直不断的升级 
    # 示例升级脚本
    if current_version == "1.0.0":
        logging.info("→ 执行 1.0.0 → 1.1.0 升级...")
        # 举例：新增字段
        # 执行标准
        set_db_version(conn, "1.1.0", "新增字段 birth_date")
    
    # 还可以继续往下扩展版本升级逻辑
    # elif current_version == "1.1.0":
    #     ...

def upgrade_private_db(conn, current_version):
    """执行数据库升级逻辑"""
    logging.info(f"公共数据库版本从 {current_version or '无版本'} 升级到 {REQUIRED_PRIVATE_DB_VERSION}")

    # 示例升级脚本
    if current_version == "1.0.0":
        logging.info("→ 执行 1.0.0 → 1.1.0 升级...")
        # 举例：新增字段
        # 执行标准
        set_db_version(conn, "1.1.0", "新增字段 birth_date")
    
    # 还可以继续往下扩展版本升级逻辑
    # elif current_version == "1.1.0":
    #     ...

def check_and_upgrade_public_db():
    conn=get_connection(DATABASE)

    current_version = get_db_version(conn)
    logging.info(f"当前公共数据库版本：{current_version}")

    if current_version != REQUIRED_PUBLIC_DB_VERSION:
        upgrade_public_db(conn, current_version)
    else:
        logging.info("公共数据库版本匹配，无需升级。")
    conn.close()

def check_and_upgrade_private_db():
    conn=get_connection(PRIVATE_DATABASE)

    current_version = get_db_version(conn)
    logging.info(f"当前私有数据库版本：{current_version}" )

    if current_version != REQUIRED_PRIVATE_DB_VERSION:
        upgrade_private_db(conn, current_version)
    else:
        logging.info("私有数据库版本匹配，无需升级。")
    conn.close()



def rebuild_privatelink():
    '''重建私有库与公有库的链接
    当公共库换了的时候，需要重建私有库的work_id
    包括三个表的更新，favourite_actress，favourite_work，masturbation,
    这三个表中更新其对应的work_id和actress_id,然后如果公共库中没有，就新建,返回需要添加的work_id列表和actress_id列表
    '''
    from core.database.db_utils import attach_private_db, detach_private_db

    added_work_ids: list[int] = []
    added_actress_ids: list[int] = []

    with get_connection(DATABASE, False) as conn:
        cursor = conn.cursor()
        attach_private_db(cursor)

        try:
            # 1. 更新 favorite_actress表中的actress_id：按 jp_name 在公库查找或新建，更新 priv.favorite_actress.actress_id
            cursor.execute("""
                SELECT favorite_actress_id, actress_id, jp_name
                FROM priv.favorite_actress
            """)
            for (fa_id, old_actress_id, jp_name) in cursor.fetchall():
                if not jp_name:
                    continue
                cursor.execute("""
                    SELECT actress_id FROM actress_name
                    WHERE jp = ? AND redirect_actress_name_id IS NULL
                    LIMIT 1
                """, (jp_name,))
                row = cursor.fetchone()
                if row:
                    new_actress_id = row[0]
                else:
                    cursor.execute("INSERT INTO actress DEFAULT VALUES")
                    new_actress_id = cursor.lastrowid
                    cursor.execute(
                        "INSERT INTO actress_name (actress_id, name_type, cn, jp) VALUES (?, 1, ?, ?)",
                        (new_actress_id, jp_name or "", jp_name),
                    )
                    added_actress_ids.append(new_actress_id)
                if new_actress_id != old_actress_id:
                    cursor.execute(
                        "UPDATE priv.favorite_actress SET actress_id = ? WHERE favorite_actress_id = ?",
                        (new_actress_id, fa_id),
                    )

            # 2. 重建 favorite_work：按 serial_number 在公库中查找或新建 work，更新 priv.favorite_work.work_id
            cursor.execute("""
                SELECT favorite_work_id, work_id, serial_number
                FROM priv.favorite_work
            """)
            for (fw_id, old_work_id, serial_number) in cursor.fetchall():
                if not serial_number:
                    continue
                cursor.execute("SELECT work_id FROM work WHERE serial_number = ?", (serial_number,))
                row = cursor.fetchone()
                if row:
                    new_work_id = row[0]
                else:
                    cursor.execute("INSERT INTO work (serial_number) VALUES (?)", (serial_number,))
                    new_work_id = cursor.lastrowid
                    added_work_ids.append(new_work_id)
                if new_work_id != old_work_id:
                    cursor.execute(
                        "UPDATE priv.favorite_work SET work_id = ? WHERE favorite_work_id = ?",
                        (new_work_id, fw_id),
                    )

            # 3. 重建 masturbation：按 serial_number 解析公库 work_id，不存在则新建 work，更新 priv.masturbation.work_id
            cursor.execute("""
                SELECT masturbation_id, work_id, serial_number
                FROM priv.masturbation
            """)
            for (m_id, old_work_id, serial_number) in cursor.fetchall():
                if not serial_number:
                    continue
                cursor.execute("SELECT work_id FROM work WHERE serial_number = ?", (serial_number,))
                row = cursor.fetchone()
                if row:
                    new_work_id = row[0]
                else:
                    cursor.execute("INSERT INTO work (serial_number) VALUES (?)", (serial_number,))
                    new_work_id = cursor.lastrowid
                    added_work_ids.append(new_work_id)
                if new_work_id != old_work_id:
                    cursor.execute(
                        "UPDATE priv.masturbation SET work_id = ? WHERE masturbation_id = ?",
                        (new_work_id, m_id),
                    )

            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.warning("rebuild_privatelink 失败: %s", e)
            raise
        finally:
            detach_private_db(cursor)

    return added_work_ids, added_actress_ids