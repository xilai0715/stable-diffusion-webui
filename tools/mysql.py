#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/3/14 12:19 PM
# @Author  : wangdongming
# @Site    : 
# @File    : mysql.py
# @Software: Hifive
import pymysql


class MySQLClient(object):

    def __init__(self, addr=None, db=None, user=None, pwd=None, port=3306):
        settings = self.get_mysql_config(addr, port, db, user, pwd)
        self.conn = pymysql.connect(**settings)

    @property
    def connect(self):
        return self.conn

    def get_mysql_config(self, addr=None, port=3306, db=None, user=None, passwd=None):
        return {
            "host": "{}".format(addr),
            "user": "{}".format(user),
            "passwd": "{}".format(passwd),
            "db": "{}".format(db),
            "charset": "utf8",
            'port': int(port),
            'autocommit': True
        }

    def execute_noquery_cmd(self, cmd, args=None, connect=None, callback=None):
        connect = connect or self.connect
        with connect.cursor() as cursor:
            r = cursor.execute(cmd, args)
            if not cursor.description:
                return r
            if not connect.autocommit_mode:
                connect.commit()
            if callback:
                callback(cmd, args, connect, cursor)
            return r

    def execute_noquery_many(self, cmd, *args):
        connect = self.connect
        with connect.cursor() as cursor:
            r = cursor.executemany(cmd, list(args))
            if not connect.autocommit_mode:
                connect.commit()
            return r

    def query(self, cmd, args=None, connect=None, fetchall=False):
        result = []

        def query_callback(cmd, args, connect, cursor):
            fields = [field_info[0] for field_info in cursor.description]
            if not fetchall:
                res = {item[0]: item[1] for item in zip(fields, cursor.fetchone())}
                result.append(res)
            else:
                res_list = [{item[0]: item[1] for item in zip(fields, info)} for info in cursor.fetchall()]
                result.extend(res_list)
        self.execute_noquery_cmd(cmd, args, connect, query_callback)
        if not result:
            return None
        elif not fetchall:
            return result[0]
        else:
            return result

    def transaction(self, *cmdArgs):
        connect = self.connect
        cursor = connect.cursor()
        try:
            for cmd, args in cmdArgs:
                cursor.execute(cmd, args)
        except Exception as ex:
            connect.rollback()
        else:
            if not connect.autocommit_mode:
                connect.commit()
        finally:
            cursor.close()

    def close(self, conn=None):
        conn = conn or self.connect
        conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()