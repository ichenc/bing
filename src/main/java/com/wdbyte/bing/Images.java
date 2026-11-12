package com.wdbyte.bing;

import java.util.Objects;

/**
 * @author niujinpeng
 * @date 2021/02/08
 * @link https://github.com/niumoo
 */
public class Images {
    private String desc;
    private String date;
    private String url;

    public static String withParams(String url, String params) {
        if (url == null) {
            return null;
        }
        return url + (url.indexOf('?') >= 0 ? "&" : "?") + params;
    }

    /**
     * cdn.bimg.cc、bing.ee123.net 的静态存档地址不识别 w/h 参数，缩放无效，
     * 大小图会是同一张 1080P，此时复用同一地址避免重复下载。
     */
    public static boolean isStaticCdn(String url) {
        return url != null
            && (url.startsWith("https://cdn.bimg.cc/") || url.startsWith("https://bing.ee123.net/"));
    }

    /**
     * 返回缩放后的小图地址；静态 CDN 无法缩放时原样返回。
     */
    public static String thumb(String url, String params) {
        return isStaticCdn(url) ? url : withParams(url, params);
    }

    @Override
    public String toString() {
        String smallUrl = withParams(url, "pid=hp&w=384&h=216&rs=1&c=4");
        //return String.format("![](%s)[%s\\| %s](%s)", smallUrl, date, desc, url);
        return String.format("![](%s)%s [download 4k](%s)", smallUrl, date, url);
    }

    public String formatMarkdown() {
        return String.format("%s | [%s](%s) ", date, desc, url);
    }

    public String toLarge() {
        String smallUrl = withParams(url, "w=1000");
        return String.format("![](%s)Today: [%s](%s)", smallUrl, desc, url);
    }

    public String getDesc() {
        return desc;
    }

    public void setDesc(String desc) {
        this.desc = desc;
    }

    public String getDate() {
        return date;
    }

    public void setDate(String date) {
        this.date = date;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    public Images() {
    }

    public Images(String desc, String date, String url) {
        this.desc = desc;
        this.date = date;
        this.url = url;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) { return true; }
        if (o == null || getClass() != o.getClass()) { return false; }
        Images images = (Images)o;
        return Objects.equals(desc, images.desc) && Objects.equals(date, images.date)
            && Objects.equals(url, images.url);
    }

    @Override
    public int hashCode() {
        return Objects.hash(desc, date, url);
    }
}
